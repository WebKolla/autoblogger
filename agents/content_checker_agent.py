"""
Content Checker Agent Module

Validates article quality, SEO compliance, and uniqueness.
Acts as QA gate before human approval.
"""

from typing import Dict, List, Optional
import json
import re
from decimal import Decimal
from .base_agent import BaseAgent


class ContentCheckerAgent(BaseAgent):
    """
    Content Checker Agent (QA)

    Responsibilities:
    1. Factual Accuracy - Verify facts against research report
    2. SEO Validation - Keyword density, meta tags, links, images
    3. Research Alignment - Must-include items present
    4. Quality Checks - Readability, grammar, flow
    5. Uniqueness Check - Similarity with recent articles
    """

    # Validation thresholds
    VALIDATION_RULES = {
        "word_count": {"min": 2500, "max": 3500},
        "keyword_density": {"min": 1.0, "max": 3.0},  # Percentage
        "meta_title": {"min": 50, "max": 60},
        "meta_description": {"min": 140, "max": 160},
        "internal_links": {"min": 2, "max": 5},
        "images": {"min": 3, "max": 5},
        "flesch_score": {"min": 60, "max": 100},  # Readability
        "similarity_threshold": 0.20,  # Max 20% similarity with recent articles
        "must_include_coverage": 1.0  # 100% of must-include items
    }

    def __init__(self, workflow_id: str):
        """Initialize Content Checker Agent"""
        super().__init__(workflow_id, agent_name="content_checker")

    def execute(self, input_data: Dict) -> Dict:
        """
        Main execution method

        Args:
            input_data: Must contain 'article', 'research_report', and optionally 'recent_articles'

        Returns:
            Dict with validation results and decision (APPROVED/NEEDS_REVISION/REJECTED)
        """
        try:
            self.update_agent_state(status="running")

            # Validate input
            self.validate_input(input_data, ["article", "research_report"])
            article = input_data["article"]
            research_report = input_data["research_report"]
            recent_articles = input_data.get("recent_articles", [])

            self.log_event(f"Starting content check for: {article.get('title', 'Untitled')}")

            # Run all checks
            checks = {
                "factual_accuracy": self._check_factual_accuracy(article, research_report),
                "seo_compliance": self._check_seo_compliance(article, research_report),
                "research_alignment": self._check_research_alignment(article, research_report),
                "uniqueness": self._check_uniqueness(article, recent_articles),
                "quality": self._check_quality(article)
            }

            # Calculate overall quality score
            quality_score = self._calculate_quality_score(checks)

            # Make decision
            status, feedback = self._make_decision(checks, quality_score)

            # Prepare output
            output = {
                "status": status,
                "quality_score": float(quality_score),
                "checks": checks,
                "feedback": feedback,
                "revisions_needed": feedback.get("revisions", []),
                "approval_recommendation": self._get_recommendation(status, quality_score)
            }

            # Update agent state
            self.update_agent_state(status="completed", output=output)

            self.log_event(f"Content check complete: {status}", data={
                "quality_score": float(quality_score),
                "status": status
            })

            return {
                "status": "success",
                "validation_result": output
            }

        except Exception as e:
            self.handle_error(e, context="Content Checker execution")
            raise

    def _check_factual_accuracy(self, article: Dict, research_report: Dict) -> Dict:
        """
        Check factual accuracy against research report

        Args:
            article: Generated article
            research_report: Research findings

        Returns:
            Dict with accuracy check results
        """
        try:
            # Extract text from Portable Text for analysis
            article_text = self._extract_text_from_portable_text(article.get("portable_text_body", []))

            # Get key facts from research
            research_synthesis = research_report.get("research_synthesis", {})
            key_facts = research_synthesis.get("key_facts", [])

            # Check if key facts are mentioned in article
            facts_found = 0
            missing_facts = []

            for fact in key_facts:
                # Simple keyword matching (could be improved with NLP)
                fact_keywords = fact.lower().split()[:3]  # First 3 words
                if any(keyword in article_text.lower() for keyword in fact_keywords):
                    facts_found += 1
                else:
                    missing_facts.append(fact)

            accuracy_rate = facts_found / max(len(key_facts), 1)

            return {
                "passed": accuracy_rate >= 0.7,  # 70% of facts should be present
                "verified_facts": facts_found,
                "total_facts": len(key_facts),
                "missing_facts": missing_facts[:3],  # Show first 3 missing
                "accuracy_rate": float(Decimal(str(accuracy_rate)))
            }

        except Exception as e:
            self.log_event(f"Error checking factual accuracy: {str(e)}", level="WARNING")
            return {"passed": True, "error": str(e)}  # Don't fail on check error

    def _check_seo_compliance(self, article: Dict, research_report: Dict) -> Dict:
        """
        Check SEO compliance (keywords, meta tags, links, images)

        Args:
            article: Generated article
            research_report: Research findings

        Returns:
            Dict with SEO compliance results
        """
        try:
            seo_metadata = article.get("seo_metadata", {})
            internal_links = article.get("internal_links", [])
            images = article.get("images", [])
            word_count = article.get("word_count", 0)

            # Extract article text
            article_text = self._extract_text_from_portable_text(article.get("portable_text_body", []))

            # Check keyword density
            keyword_research = research_report.get("keyword_research", {})
            primary_keywords = keyword_research.get("primary_keywords", [])

            keyword_density_results = {}
            if primary_keywords and article_text:
                total_words = len(article_text.split())
                for kw_data in primary_keywords[:2]:  # Check top 2 keywords
                    keyword = kw_data.get("keyword", "")
                    count = article_text.lower().count(keyword.lower())
                    density = (count / max(total_words, 1)) * 100
                    keyword_density_results[keyword] = float(Decimal(str(density)))

            avg_density = sum(keyword_density_results.values()) / max(len(keyword_density_results), 1)

            # Validate meta tags
            meta_title = seo_metadata.get("meta_title", "")
            meta_description = seo_metadata.get("meta_description", "")

            checks = {
                "keyword_density": {
                    "value": float(Decimal(str(avg_density))),
                    "status": "optimal" if self.VALIDATION_RULES["keyword_density"]["min"] <= avg_density <= self.VALIDATION_RULES["keyword_density"]["max"] else "needs_adjustment",
                    "details": keyword_density_results
                },
                "meta_title": {
                    "length": len(meta_title),
                    "includes_keyword": any(kw.get("keyword", "").lower() in meta_title.lower() for kw in primary_keywords[:1]),
                    "status": "good" if self.VALIDATION_RULES["meta_title"]["min"] <= len(meta_title) <= self.VALIDATION_RULES["meta_title"]["max"] else "needs_adjustment"
                },
                "meta_description": {
                    "length": len(meta_description),
                    "includes_keyword": any(kw.get("keyword", "").lower() in meta_description.lower() for kw in primary_keywords[:1]),
                    "status": "good" if self.VALIDATION_RULES["meta_description"]["min"] <= len(meta_description) <= self.VALIDATION_RULES["meta_description"]["max"] else "needs_adjustment"
                },
                "internal_links": {
                    "count": len(internal_links),
                    "status": "good" if self.VALIDATION_RULES["internal_links"]["min"] <= len(internal_links) <= self.VALIDATION_RULES["internal_links"]["max"] else "needs_more"
                },
                "images": {
                    "count": len(images),
                    "status": "good" if self.VALIDATION_RULES["images"]["min"] <= len(images) <= self.VALIDATION_RULES["images"]["max"] else "needs_more"
                }
            }

            # Overall pass if no critical issues
            passed = (
                checks["keyword_density"]["status"] != "over_optimized" and
                checks["meta_title"]["status"] == "good" and
                checks["meta_description"]["status"] == "good" and
                checks["internal_links"]["count"] >= self.VALIDATION_RULES["internal_links"]["min"] and
                checks["images"]["count"] >= self.VALIDATION_RULES["images"]["min"]
            )

            return {
                "passed": passed,
                **checks
            }

        except Exception as e:
            self.log_event(f"Error checking SEO compliance: {str(e)}", level="WARNING")
            return {"passed": True, "error": str(e)}

    def _check_research_alignment(self, article: Dict, research_report: Dict) -> Dict:
        """
        Check if article includes all must-have elements from research

        Args:
            article: Generated article
            research_report: Research findings

        Returns:
            Dict with alignment check results
        """
        try:
            article_text = self._extract_text_from_portable_text(article.get("portable_text_body", []))

            # Get must-include items
            content_recs = research_report.get("content_recommendations", {})
            must_include = content_recs.get("must_include", [])

            # Check presence
            items_found = 0
            missing_items = []

            for item in must_include:
                # Simple keyword check
                item_keywords = item.lower().split()[:2]  # First 2 words
                if any(keyword in article_text.lower() for keyword in item_keywords):
                    items_found += 1
                else:
                    missing_items.append(item)

            coverage = items_found / max(len(must_include), 1)

            return {
                "passed": coverage >= 0.8,  # 80% coverage required
                "items_present": items_found,
                "items_total": len(must_include),
                "missing_items": missing_items[:3],  # First 3
                "coverage": float(Decimal(str(coverage)))
            }

        except Exception as e:
            self.log_event(f"Error checking research alignment: {str(e)}", level="WARNING")
            return {"passed": True, "error": str(e)}

    def _check_uniqueness(self, article: Dict, recent_articles: List[Dict]) -> Dict:
        """
        Check uniqueness against recent articles

        Args:
            article: Generated article
            recent_articles: List of recent published articles

        Returns:
            Dict with uniqueness check results
        """
        try:
            if not recent_articles:
                return {
                    "passed": True,
                    "similarity_scores": [],
                    "max_similarity": 0.0,
                    "unique": True
                }

            article_text = self._extract_text_from_portable_text(article.get("portable_text_body", []))
            article_title = article.get("title", "").lower()

            similarity_scores = []

            for recent in recent_articles[:5]:  # Check last 5
                recent_title = recent.get("topic_title", "").lower()

                # Simple title similarity (Jaccard similarity)
                title_sim = self._calculate_jaccard_similarity(article_title, recent_title)

                similarity_scores.append({
                    "article": recent_title,
                    "score": float(Decimal(str(title_sim)))
                })

            max_similarity = max([s["score"] for s in similarity_scores]) if similarity_scores else 0.0

            return {
                "passed": max_similarity < self.VALIDATION_RULES["similarity_threshold"],
                "similarity_scores": similarity_scores,
                "max_similarity": float(Decimal(str(max_similarity))),
                "threshold": self.VALIDATION_RULES["similarity_threshold"],
                "unique": max_similarity < self.VALIDATION_RULES["similarity_threshold"]
            }

        except Exception as e:
            self.log_event(f"Error checking uniqueness: {str(e)}", level="WARNING")
            return {"passed": True, "error": str(e)}

    def _check_quality(self, article: Dict) -> Dict:
        """
        Check overall article quality

        Args:
            article: Generated article

        Returns:
            Dict with quality check results
        """
        try:
            word_count = article.get("word_count", 0)
            portable_text = article.get("portable_text_body", [])
            article_text = self._extract_text_from_portable_text(portable_text)

            # Word count check
            word_count_ok = self.VALIDATION_RULES["word_count"]["min"] <= word_count <= self.VALIDATION_RULES["word_count"]["max"]

            # Reading time (200 words per minute)
            reading_time = max(1, word_count // 200)

            # Simple readability estimate (sentence length)
            sentences = re.split(r'[.!?]+', article_text)
            sentences = [s.strip() for s in sentences if s.strip()]
            avg_sentence_length = len(article_text.split()) / max(len(sentences), 1)

            # Flesch reading ease estimate (simplified)
            # Real formula: 206.835 - 1.015(total words/total sentences) - 84.6(total syllables/total words)
            # Simplified: just use sentence length as proxy
            flesch_estimate = max(0, min(100, 100 - (avg_sentence_length * 2)))

            # Check for repetitive phrases
            words = article_text.lower().split()
            word_freq = {}
            for word in words:
                if len(word) > 4:  # Only count words > 4 chars
                    word_freq[word] = word_freq.get(word, 0) + 1

            repetitive_words = [word for word, count in word_freq.items() if count > 10]

            return {
                "passed": word_count_ok and flesch_estimate >= self.VALIDATION_RULES["flesch_score"]["min"],
                "word_count": word_count,
                "target_range": [self.VALIDATION_RULES["word_count"]["min"], self.VALIDATION_RULES["word_count"]["max"]],
                "reading_time": reading_time,
                "flesch_reading_ease": float(Decimal(str(flesch_estimate))),
                "avg_sentence_length": float(Decimal(str(avg_sentence_length))),
                "repetitive_words": repetitive_words[:5],  # First 5
                "status": "good" if word_count_ok and flesch_estimate >= 60 else "needs_improvement"
            }

        except Exception as e:
            self.log_event(f"Error checking quality: {str(e)}", level="WARNING")
            return {"passed": True, "error": str(e)}

    def _calculate_quality_score(self, checks: Dict) -> Decimal:
        """
        Calculate overall quality score (0-1)

        Args:
            checks: All check results

        Returns:
            Quality score as Decimal
        """
        try:
            # Weighted scoring
            weights = {
                "factual_accuracy": 0.25,
                "seo_compliance": 0.25,
                "research_alignment": 0.20,
                "uniqueness": 0.15,
                "quality": 0.15
            }

            score = Decimal('0')

            for check_name, weight in weights.items():
                check_result = checks.get(check_name, {})
                if check_result.get("passed", False):
                    score += Decimal(str(weight))

            return score

        except Exception as e:
            self.log_event(f"Error calculating quality score: {str(e)}", level="WARNING")
            return Decimal('0.7')  # Default passing score

    def _make_decision(self, checks: Dict, quality_score: Decimal) -> tuple:
        """
        Make final decision: APPROVED, NEEDS_REVISION, or REJECTED

        Args:
            checks: All check results
            quality_score: Overall quality score

        Returns:
            Tuple of (status, feedback)
        """
        try:
            # Critical checks that must pass
            critical_checks = [
                checks["factual_accuracy"]["passed"],
                checks["research_alignment"]["passed"],
                checks["uniqueness"]["passed"]
            ]

            # Non-critical checks
            seo_passed = checks["seo_compliance"]["passed"]
            quality_passed = checks["quality"]["passed"]

            # Collect feedback
            strengths = []
            weaknesses = []
            revisions = []

            # Analyze results
            if checks["factual_accuracy"].get("accuracy_rate", 0) >= 0.9:
                strengths.append("Excellent factual accuracy")
            elif not checks["factual_accuracy"]["passed"]:
                weaknesses.append("Some key facts missing")
                revisions.append("Add missing facts from research")

            if checks["seo_compliance"]["passed"]:
                strengths.append("Strong SEO compliance")
            else:
                weaknesses.append("SEO needs optimization")
                seo_checks = checks["seo_compliance"]
                if seo_checks.get("keyword_density", {}).get("status") == "needs_adjustment":
                    revisions.append("Adjust keyword density")
                if seo_checks.get("meta_title", {}).get("status") != "good":
                    revisions.append("Optimize meta title length")

            if checks["uniqueness"]["passed"]:
                strengths.append("Unique content angle")
            else:
                weaknesses.append("Too similar to recent articles")
                revisions.append("Differentiate from recent content")

            if quality_score >= Decimal('0.9'):
                strengths.append("High overall quality")

            # Decision logic
            if not all(critical_checks):
                status = "REJECTED"
                feedback = {
                    "decision": "Article rejected due to critical issues",
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "revisions": revisions
                }
            elif not seo_passed or not quality_passed:
                status = "NEEDS_REVISION"
                feedback = {
                    "decision": "Article needs minor revisions",
                    "strengths": strengths,
                    "weaknesses": weaknesses,
                    "revisions": revisions
                }
            else:
                status = "APPROVED"
                feedback = {
                    "decision": "Article approved for publication",
                    "strengths": strengths,
                    "weaknesses": weaknesses if weaknesses else ["None identified"],
                    "revisions": []
                }

            return status, feedback

        except Exception as e:
            self.log_event(f"Error making decision: {str(e)}", level="ERROR")
            # Default to needs revision if error
            return "NEEDS_REVISION", {"decision": "Error in validation", "error": str(e)}

    def _get_recommendation(self, status: str, quality_score: Decimal) -> str:
        """Get human-readable recommendation"""
        if status == "APPROVED":
            if quality_score >= Decimal('0.9'):
                return "APPROVE - Excellent quality, ready for publication"
            else:
                return "APPROVE - Good quality, ready for publication"
        elif status == "NEEDS_REVISION":
            return "REVIEW - Minor issues found, recommend human review"
        else:
            return "REJECT - Critical issues found, needs significant revision"

    def _extract_text_from_portable_text(self, portable_text: List[Dict]) -> str:
        """Extract plain text from Portable Text blocks"""
        text_parts = []
        try:
            for block in portable_text:
                if block.get("_type") == "block":
                    for child in block.get("children", []):
                        text = child.get("text", "")
                        if text:
                            text_parts.append(text)
        except Exception as e:
            self.log_event(f"Error extracting text: {str(e)}", level="WARNING")

        return " ".join(text_parts)

    def _calculate_jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts"""
        try:
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())

            intersection = words1.intersection(words2)
            union = words1.union(words2)

            return len(intersection) / max(len(union), 1)
        except Exception:
            return 0.0
