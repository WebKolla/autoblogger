"""
SEO Writer Agent Module

Writes comprehensive, SEO-optimized articles using Claude AI.
Integrates research findings, sources images, and generates Portable Text JSON.
"""

from typing import Dict, List, Optional
import requests
import json
import random
import re
from decimal import Decimal
from .base_agent import BaseAgent


class SEOWriterAgent(BaseAgent):
    """
    SEO Writer Agent

    Responsibilities:
    1. Write 2,500-3,500 word SEO-optimized articles
    2. Integrate research findings naturally
    3. Source images from Cloudinary (priority) + Pexels (fallback)
    4. Add 2-3 internal links to Across Ceylon pages
    5. Generate Sanity Portable Text JSON format
    6. Create SEO metadata (title, description, keywords)
    """

    def __init__(self, workflow_id: str):
        """Initialize SEO Writer Agent"""
        super().__init__(workflow_id, agent_name="writer")

        # Load image sourcing credentials
        try:
            self.pexels_key = self.get_secrets("blog-pexels-key")["key"]
            self.log_event("Pexels API credentials loaded")
        except Exception as e:
            self.log_event(f"Pexels API credentials not found: {str(e)}", level="ERROR")
            self.pexels_key = None

        try:
            cloudinary_secret = self.get_secrets("blog-cloudinary-credentials")
            self.cloudinary_cloud_name = cloudinary_secret.get("cloud_name")
            self.cloudinary_api_key = cloudinary_secret.get("api_key")
            self.cloudinary_api_secret = cloudinary_secret.get("api_secret")
            self.log_event("Cloudinary credentials loaded")
        except Exception as e:
            self.log_event(f"Cloudinary credentials not found: {str(e)}", level="WARNING")
            self.cloudinary_cloud_name = None

        # Sitemap URLs for internal linking
        self.internal_link_urls = [
            {"anchor": "cultural triangle cycling tour", "url": "https://acrossceylon.com/packages/cultural-triangle"},
            {"anchor": "hill country bike tour", "url": "https://acrossceylon.com/routes/hill-country"},
            {"anchor": "custom cycling tours", "url": "https://acrossceylon.com/packages/custom-tour"},
            {"anchor": "coastal cycling routes", "url": "https://acrossceylon.com/routes/south-coast"},
            {"anchor": "multi-day cycling expeditions", "url": "https://acrossceylon.com/packages/multi-day"},
        ]

    def execute(self, input_data: Dict) -> Dict:
        """
        Main execution method

        Args:
            input_data: Must contain 'research_report' from Research Agent

        Returns:
            Dict with complete article and metadata
        """
        try:
            self.update_agent_state(status="running")

            # Validate input
            self.validate_input(input_data, ["research_report"])
            research_report = input_data["research_report"]

            self.log_event(f"Starting article writing for: {research_report['topic_title']}")

            # Step 1: Generate article with Claude
            article_data = self._generate_article(research_report)

            # Step 2: Source images
            images = self._source_images(research_report, article_data)

            # Step 3: Add images to article data
            article_data["images"] = images

            # Step 4: Build complete output
            output = {
                "article": article_data,
                "images": images,
                "metadata": {
                    "word_count": article_data.get("word_count", 0),
                    "reading_time": article_data.get("reading_time", 0),
                    "images_sourced": len(images),
                    "internal_links_added": len(article_data.get("internal_links", []))
                }
            }

            # Update agent state
            self.update_agent_state(status="completed", output=output)

            return {
                "status": "success",
                "article": article_data,
                "images": images,
                "metadata": output["metadata"]
            }

        except Exception as e:
            self.handle_error(e, context="SEO Writer Agent execution")
            raise

    def _generate_article(self, research_report: Dict) -> Dict:
        """
        Generate article using Claude

        Args:
            research_report: Research findings from Research Agent

        Returns:
            Dict with article data including Portable Text
        """
        try:
            # Build Claude prompt
            prompt = self._build_writing_prompt(research_report)

            self.log_event("Invoking Claude for article generation")

            # Invoke Claude with high token limit for full article
            response = self.invoke_claude(
                prompt=prompt,
                max_tokens=16000,  # High limit for complete article
                temperature=0.7,
                system="You are an expert travel writer specializing in cycling tourism. Write engaging, SEO-optimized content that inspires and informs readers."
            )

            # Parse Claude's response
            try:
                article_data = json.loads(response)
                self.log_event(f"Article generated: {article_data.get('word_count', 0)} words")
            except json.JSONDecodeError:
                self.log_event("Claude response not valid JSON, attempting to extract", level="WARNING")
                # Try to extract JSON from response
                json_match = re.search(r'\{.*\}', response, re.DOTALL)
                if json_match:
                    article_data = json.loads(json_match.group())
                else:
                    raise ValueError("Could not parse article data from Claude response")

            # Validate required fields
            required_fields = ["title", "portable_text_body", "seo_metadata"]
            for field in required_fields:
                if field not in article_data:
                    raise ValueError(f"Missing required field in article: {field}")

            # Calculate word count if not provided
            if "word_count" not in article_data:
                article_data["word_count"] = self._estimate_word_count(article_data["portable_text_body"])

            # Calculate reading time (avg 200 words per minute)
            article_data["reading_time"] = max(1, article_data["word_count"] // 200)

            return article_data

        except Exception as e:
            self.log_event(f"Error generating article: {str(e)}", level="ERROR")
            raise

    def _build_writing_prompt(self, research_report: Dict) -> str:
        """Build comprehensive writing prompt for Claude"""

        topic_title = research_report["topic_title"]
        topic_category = research_report["topic_category"]
        keyword_research = research_report["keyword_research"]
        research_synthesis = research_report.get("research_synthesis", {})
        content_recs = research_report.get("content_recommendations", {})

        primary_keywords = [kw["keyword"] for kw in keyword_research.get("primary_keywords", [])]
        secondary_keywords = keyword_research.get("secondary_keywords", [])

        # Select 2-3 internal links randomly
        selected_internal_links = random.sample(self.internal_link_urls, min(3, len(self.internal_link_urls)))

        prompt = f"""Write a comprehensive SEO-optimized blog article for Across Ceylon, a premium cycling tour operator in Sri Lanka.

ARTICLE TOPIC: {topic_title}
CATEGORY: {topic_category}

TARGET KEYWORDS:
Primary (use naturally, ~1.5% density): {', '.join(primary_keywords)}
Secondary: {', '.join(secondary_keywords)}

RESEARCH FINDINGS:
{json.dumps(research_synthesis, indent=2)}

CONTENT REQUIREMENTS:
- Length: {content_recs.get('target_length', '2500-3000 words')}
- Tone: {content_recs.get('tone', 'Educational + Inspirational')}
- Structure: {content_recs.get('structure', 'Introduction → 8-10 sections → Practical tips → CTA')}
- Must Include: {', '.join(content_recs.get('must_include', []))}

INTERNAL LINKS (add 2-3 naturally in the content):
{json.dumps(selected_internal_links, indent=2)}

CRITICAL FORMATTING RULES:
1. DO NOT use markdown syntax (no ###, ##, **, -, etc.)
2. Output ONLY valid Sanity Portable Text JSON format
3. Section headers MUST be style: "h2" or "h3" blocks, NOT markdown
4. Lists must be proper listItem blocks, NOT markdown bullets
5. Bold text uses marks: ["strong"], NOT ** syntax
6. Ensure all JSON is complete and valid (no truncation)

PORTABLE TEXT STRUCTURE:
Each content block should be:
{{
  "_key": "unique-key-{random}",
  "_type": "block",
  "style": "normal" | "h2" | "h3",
  "children": [
    {{
      "_type": "span",
      "_key": "span-key",
      "text": "Your text here",
      "marks": []  // or ["strong"] for bold
    }}
  ],
  "markDefs": []  // or array with link definitions
}}

For internal links, use markDefs:
{{
  "_key": "link-key",
  "_type": "block",
  "markDefs": [
    {{
      "_key": "mark-key",
      "_type": "link",
      "href": "https://acrossceylon.com/..."
    }}
  ],
  "children": [
    {{
      "_key": "span-key",
      "_type": "span",
      "text": "link text",
      "marks": ["mark-key"]
    }}
  ]
}}

OUTPUT FORMAT (JSON):
{{
  "title": "Engaging SEO-optimized title (<60 chars, includes primary keyword)",
  "portable_text_body": [
    // Array of Portable Text blocks
  ],
  "word_count": 2847,
  "image_search_terms": ["term1", "term2", "term3"],  // For image sourcing
  "internal_links": [
    {{
      "anchor": "link text",
      "url": "https://acrossceylon.com/...",
      "context": "Sentence where link appears"
    }}
  ],
  "seo_metadata": {{
    "meta_title": "SEO title 50-60 chars with primary keyword",
    "meta_description": "Compelling 140-160 char description with primary keyword and CTA",
    "focus_keyword": "{primary_keywords[0] if primary_keywords else 'cycling sri lanka'}",
    "keywords": ["{primary_keywords[0] if primary_keywords else ''}", "keyword2", "keyword3", "keyword4"]
  }}
}}

WRITING GUIDELINES:
- Start with compelling hook (problem/dream/surprising fact)
- Use storytelling and vivid descriptions
- Include practical, actionable information
- Natural keyword integration (NO keyword stuffing)
- Write for humans first, search engines second
- Mention Across Ceylon naturally (2-3 times)
- End with clear call-to-action
- Be specific and detailed (avoid generic advice)
- Use varied sentence structure
- Include local insights and cultural context

Write the complete article now. Ensure JSON is valid and complete (no truncation)."""

        return prompt

    def _estimate_word_count(self, portable_text: List[Dict]) -> int:
        """Estimate word count from Portable Text blocks"""
        total_words = 0
        try:
            for block in portable_text:
                if block.get("_type") == "block":
                    for child in block.get("children", []):
                        text = child.get("text", "")
                        total_words += len(text.split())
        except Exception as e:
            self.log_event(f"Error estimating word count: {str(e)}", level="WARNING")
            return 2500  # Fallback estimate

        return total_words

    def _source_images(self, research_report: Dict, article_data: Dict) -> List[Dict]:
        """
        Source images from Cloudinary and Pexels

        Args:
            research_report: Research findings
            article_data: Generated article with image_search_terms

        Returns:
            List of image dicts
        """
        try:
            images = []
            search_terms = article_data.get("image_search_terms", [])[:3]

            if not search_terms:
                # Fallback search terms from topic
                search_terms = ["cycling", "sri lanka", research_report.get("topic_category", "tour")]

            self.log_event(f"Sourcing images for terms: {search_terms}")

            # Step 1: Try Cloudinary first (priority)
            if self.cloudinary_cloud_name:
                try:
                    cloudinary_images = self._fetch_cloudinary_images(search_terms)
                    images.extend(cloudinary_images)
                    self.log_event(f"Added {len(cloudinary_images)} images from Cloudinary")
                except Exception as e:
                    self.log_event(f"Cloudinary fetch error: {str(e)}", level="WARNING")

            # Step 2: Fill remaining slots with Pexels
            if len(images) < 5 and self.pexels_key:
                try:
                    pexels_images = self._fetch_pexels_images(search_terms, limit=5 - len(images))
                    images.extend(pexels_images)
                    self.log_event(f"Added {len(pexels_images)} images from Pexels")
                except Exception as e:
                    self.log_event(f"Pexels fetch error: {str(e)}", level="WARNING")

            self.log_event(f"Total images sourced: {len(images)}")
            return images[:5]  # Max 5 images

        except Exception as e:
            self.log_event(f"Error sourcing images: {str(e)}", level="ERROR")
            return []

    def _fetch_cloudinary_images(self, search_terms: List[str]) -> List[Dict]:
        """Fetch images from Cloudinary"""
        images = []

        try:
            response = requests.get(
                f"https://api.cloudinary.com/v1_1/{self.cloudinary_cloud_name}/resources/image",
                params={
                    "type": "upload",
                    "max_results": 30,
                },
                auth=(self.cloudinary_api_key, self.cloudinary_api_secret),
                timeout=10
            )

            if response.status_code == 200:
                resources = response.json().get("resources", [])
                self.log_event(f"Found {len(resources)} images in Cloudinary")

                # Randomly select 3 images for variety
                selected = random.sample(resources, min(3, len(resources)))

                for resource in selected:
                    public_id = resource.get("public_id")
                    images.append({
                        "url": f"https://res.cloudinary.com/{self.cloudinary_cloud_name}/image/upload/w_1200,q_auto,f_auto/{public_id}",
                        "alt": "Cycling in Sri Lanka - Across Ceylon",
                        "credit": "Photo by Across Ceylon",
                        "credit_url": "https://acrossceylon.com",
                        "source": "cloudinary"
                    })
            else:
                self.log_event(f"Cloudinary API error: {response.status_code}", level="WARNING")

        except Exception as e:
            self.log_event(f"Cloudinary API error: {str(e)}", level="WARNING")

        return images

    def _fetch_pexels_images(self, search_terms: List[str], limit: int = 5) -> List[Dict]:
        """Fetch images from Pexels API"""
        images = []

        try:
            for term in search_terms:
                if len(images) >= limit:
                    break

                response = requests.get(
                    "https://api.pexels.com/v1/search",
                    headers={"Authorization": self.pexels_key},
                    params={
                        "query": f"sri lanka {term}",
                        "per_page": 2,
                        "orientation": "landscape",
                    },
                    timeout=10,
                )

                if response.status_code == 200:
                    photos = response.json().get("photos", [])
                    for photo in photos:
                        if len(images) >= limit:
                            break
                        images.append({
                            "url": photo["src"]["large"],
                            "alt": f"{term} in Sri Lanka - cycling destination",
                            "credit": f"Photo by {photo['photographer']} from Pexels",
                            "credit_url": photo["photographer_url"],
                            "source": "pexels"
                        })
                else:
                    self.log_event(f"Pexels API error for '{term}': {response.status_code}", level="WARNING")

        except Exception as e:
            self.log_event(f"Pexels API error: {str(e)}", level="WARNING")

        return images
