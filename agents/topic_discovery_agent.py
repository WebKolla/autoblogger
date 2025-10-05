"""
Topic Discovery Agent Module

Discovers unique article topics by analyzing published content,
identifying content gaps, and cleaning stale workflows.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone, timedelta
from boto3.dynamodb.conditions import Attr, Key
from decimal import Decimal
import json
import random
from .base_agent import BaseAgent


# Static topic bank as fallback
TOPIC_BANK = [
    {
        "title": "Cycling Through Sri Lanka's Cultural Triangle",
        "keywords": ["sri lanka cultural triangle cycling", "anuradhapura polonnaruwa bike tour",
                    "ancient cities cycling route", "sigiriya cycling experience"],
        "category": "Cultural Routes",
    },
    {
        "title": "Hill Country Cycling Adventure Through Ceylon's Tea Estates",
        "keywords": ["sri lanka hill country cycling", "nuwara eliya bike tour",
                    "tea plantation cycling route", "ella to kandy cycling"],
        "category": "Hill Country",
    },
    {
        "title": "Coast to Coast: Sri Lanka's Ultimate Cycling Journey",
        "keywords": ["coast to coast cycling sri lanka", "cross country bike tour",
                    "sri lanka cycling holiday", "galle to trincomalee cycling"],
        "category": "Epic Routes",
    },
    {
        "title": "Cycling Sri Lanka's Southern Coast and Beaches",
        "keywords": ["south coast cycling sri lanka", "galle mirissa bike route",
                    "beach cycling holiday", "coastal cycling tour"],
        "category": "Coastal Routes",
    },
    {
        "title": "Knuckles Mountain Range: Sri Lanka's Premier Cycling Challenge",
        "keywords": ["knuckles mountain range cycling", "mountain biking sri lanka",
                    "challenging cycling routes", "knuckles bike tour"],
        "category": "Mountain Biking",
    },
    {
        "title": "Wildlife Cycling Safari: Yala to Udawalawe Adventure",
        "keywords": ["wildlife cycling sri lanka", "yala national park bike tour",
                    "elephant cycling safari", "udawalawe cycling route"],
        "category": "Wildlife",
    },
    {
        "title": "Cycling Sri Lanka: Complete Planning Guide for First-Timers",
        "keywords": ["cycling sri lanka guide", "plan bike tour sri lanka",
                    "sri lanka cycling tips", "bike holiday planning"],
        "category": "Planning",
    },
    {
        "title": "When to Cycle Sri Lanka: Seasonal Guide and Weather Patterns",
        "keywords": ["best time cycling sri lanka", "sri lanka cycling season",
                    "monsoon cycling routes", "dry season bike tours"],
        "category": "Planning",
    },
    {
        "title": "Gravel Cycling Adventures in Rural Sri Lanka",
        "keywords": ["gravel biking sri lanka", "gravel cycling routes",
                    "rural cycling adventures", "off-road bike tours"],
        "category": "Adventure",
    },
    {
        "title": "Cycling Through Sri Lanka's Spice Gardens and Plantations",
        "keywords": ["spice garden cycling tour", "cinnamon plantation cycling",
                    "agricultural cycling routes", "farm to table bike tour"],
        "category": "Cultural Experience",
    },
    {
        "title": "Family Cycling Holidays in Sri Lanka: Safe Routes and Activities",
        "keywords": ["family cycling sri lanka", "kid friendly bike tours",
                    "safe cycling routes families", "family bike holiday asia"],
        "category": "Family Travel",
    },
    {
        "title": "E-Bike Tours: Exploring Sri Lanka Without Breaking a Sweat",
        "keywords": ["e-bike tours sri lanka", "electric bicycle touring",
                    "assisted cycling holiday", "ebike rental sri lanka"],
        "category": "E-Bike",
    },
    {
        "title": "Cycling and Yoga Retreats: Wellness in Sri Lanka",
        "keywords": ["cycling yoga retreat sri lanka", "wellness bike tour",
                    "active meditation holiday", "mindful cycling vacation"],
        "category": "Wellness",
    },
    {
        "title": "Cycling Sri Lanka's Coffee Triangle: From Bean to Cup",
        "keywords": ["coffee cycling tour sri lanka", "coffee plantation bike route",
                    "specialty coffee cycling", "haputale cycling experience"],
        "category": "Culinary",
    },
    {
        "title": "Multi-Day Cycling Expeditions Across Sri Lanka",
        "keywords": ["multi day cycling tour sri lanka", "week long bike expedition",
                    "cycling expedition asia", "supported bike tour sri lanka"],
        "category": "Epic Routes",
    },
    {
        "title": "Cycling Safety and Road Conditions in Sri Lanka",
        "keywords": ["cycling safety sri lanka", "road conditions bike touring",
                    "safe cycling tips asia", "sri lanka traffic cycling"],
        "category": "Safety",
    },
    {
        "title": "Solo Cycling in Sri Lanka: Independent Travel Guide",
        "keywords": ["solo cycling sri lanka", "independent bike tour",
                    "self guided cycling route", "solo traveler bike holiday"],
        "category": "Solo Travel",
    },
    {
        "title": "Cycling and Wildlife Photography Safari in Sri Lanka",
        "keywords": ["cycling photography tour", "wildlife photography cycling",
                    "photo safari bike tour", "photography cycling holiday"],
        "category": "Photography",
    },
    {
        "title": "Budget-Friendly Cycling Tours and Backroads of Sri Lanka",
        "keywords": ["budget cycling sri lanka", "affordable bike tours",
                    "backroads cycling routes", "cheap cycling holiday"],
        "category": "Budget Travel",
    },
    {
        "title": "Luxury Cycling Holidays: Five-Star Tours of Sri Lanka",
        "keywords": ["luxury cycling sri lanka", "premium bike tours",
                    "five star cycling holiday", "luxury bike tour asia"],
        "category": "Luxury",
    },
    {
        "title": "Cycling Through Sri Lanka's Rice Paddies and Farming Villages",
        "keywords": ["rice paddy cycling tour", "farming village bike route",
                    "rural cycling sri lanka", "agricultural cycling"],
        "category": "Rural Routes",
    },
    {
        "title": "Cycling the Adam's Peak Pilgrimage Route",
        "keywords": ["adams peak cycling", "pilgrimage cycling route",
                    "sri pada bike tour", "spiritual cycling journey"],
        "category": "Cultural Routes",
    },
    {
        "title": "Night Sky Cycling: Stargazing Tours in Rural Sri Lanka",
        "keywords": ["night cycling sri lanka", "stargazing bike tour",
                    "astronomy cycling experience", "dark sky cycling"],
        "category": "Unique Experiences",
    },
    {
        "title": "Cycling and Ayurveda: Holistic Wellness Tours",
        "keywords": ["ayurveda cycling retreat", "holistic wellness bike tour",
                    "traditional healing cycling", "ayurvedic cycling holiday"],
        "category": "Wellness",
    },
]


class TopicDiscoveryAgent(BaseAgent):
    """
    Topic Discovery Agent

    Responsibilities:
    1. Clean up stale workflows (>24h old)
    2. Analyze published articles for patterns
    3. Identify content gaps
    4. Generate or select unique topics
    5. Ensure no duplicates or similar topics
    """

    def __init__(self, workflow_id: str):
        """Initialize Topic Discovery Agent"""
        super().__init__(workflow_id, agent_name="topic_discovery")

    def execute(self, input_data: Dict) -> Dict:
        """
        Main execution method

        Args:
            input_data: Not used (agent runs independently)

        Returns:
            Dict with selected topic and analysis
        """
        try:
            self.update_agent_state(status="running")

            # Step 1: Cleanup stale workflows
            self.log_event("Starting workflow cleanup")
            cleanup_result = self._cleanup_stale_workflows()

            # Step 2: Analyze published articles
            self.log_event("Analyzing published articles")
            published_articles = self._get_published_articles()
            analysis = self._analyze_articles(published_articles)

            # Step 3: Generate/select topic
            self.log_event("Selecting unique topic")
            selected_topic = self._select_unique_topic(analysis, published_articles)

            # Prepare output
            output = {
                "cleanup_summary": cleanup_result,
                "analysis": analysis,
                "selected_topic": selected_topic
            }

            # Update agent state
            self.update_agent_state(status="completed", output=output)

            return {
                "status": "success",
                "cleanup_summary": cleanup_result,
                "analysis": analysis,
                "selected_topic": selected_topic
            }

        except Exception as e:
            self.handle_error(e, context="Topic Discovery execution")
            raise

    def _cleanup_stale_workflows(self) -> Dict:
        """
        Clean up stale 'awaiting_approval' workflows older than 24 hours

        Returns:
            Dict with cleanup summary
        """
        try:
            cutoff_time = datetime.now(timezone.utc) - timedelta(hours=24)
            cutoff_timestamp = cutoff_time.isoformat()

            # Scan for stale workflows
            response = self.workflow_table.scan(
                FilterExpression=Attr('status').eq('awaiting_approval') &
                                Attr('created_at').lt(cutoff_timestamp)
            )

            stale_workflows = response.get('Items', [])
            deleted_count = 0

            for workflow in stale_workflows:
                try:
                    self.workflow_table.delete_item(
                        Key={'workflow_id': workflow['workflow_id']}
                    )
                    deleted_count += 1
                    self.log_event(
                        f"Deleted stale workflow: {workflow['workflow_id']}",
                        data={"created_at": workflow.get('created_at')}
                    )
                except Exception as e:
                    self.log_event(
                        f"Failed to delete workflow {workflow['workflow_id']}: {str(e)}",
                        level="WARNING"
                    )

            cleanup_summary = {
                "deleted_workflows": deleted_count,
                "cutoff_time": cutoff_timestamp,
                "reason": "Stale awaiting_approval >24h"
            }

            self.log_event(f"Cleanup complete: {deleted_count} workflows deleted")

            return cleanup_summary

        except Exception as e:
            self.log_event(f"Cleanup error: {str(e)}", level="ERROR")
            return {
                "deleted_workflows": 0,
                "error": str(e)
            }

    def _get_published_articles(self, limit: int = 30) -> List[Dict]:
        """
        Get recently published articles from DynamoDB

        Args:
            limit: Maximum number of articles to retrieve (default 30)

        Returns:
            List of published article data
        """
        try:
            # Scan for published articles
            response = self.workflow_table.scan(
                FilterExpression=Attr('status').eq('published'),
                Limit=limit
            )

            articles = response.get('Items', [])

            # Sort by created_at (most recent first)
            articles.sort(
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )

            self.log_event(f"Retrieved {len(articles)} published articles")

            return articles[:limit]

        except Exception as e:
            self.log_event(f"Error retrieving published articles: {str(e)}", level="ERROR")
            return []

    def _analyze_articles(self, articles: List[Dict]) -> Dict:
        """
        Analyze published articles for patterns and gaps

        Args:
            articles: List of published articles

        Returns:
            Dict with analysis results
        """
        try:
            # Count categories
            category_counts = {}
            all_titles = []
            all_keywords = []

            for article in articles:
                # Handle both old schema (string) and new schema (dict)
                if isinstance(article, str):
                    # Skip malformed entries
                    continue

                topic_category = article.get('topic_category', 'Unknown')
                category_counts[topic_category] = category_counts.get(topic_category, 0) + 1

                topic_title = article.get('topic_title', '')
                if topic_title:
                    all_titles.append(topic_title.lower())

                # Extract keywords if available
                article_data = article.get('article_data', {})
                if isinstance(article_data, dict):
                    seo_metadata = article_data.get('seo_metadata', {})
                    if isinstance(seo_metadata, dict):
                        keywords = seo_metadata.get('keywords', [])
                        if isinstance(keywords, list):
                            all_keywords.extend([str(k).lower() for k in keywords])

            # Identify content gaps (categories with few articles)
            all_categories = set([t['category'] for t in TOPIC_BANK])
            covered_categories = set(category_counts.keys())
            gap_categories = all_categories - covered_categories

            # Find underrepresented categories (<=1 article)
            underrep_categories = [cat for cat, count in category_counts.items() if count <= 1]

            analysis = {
                "total_articles": len(articles),
                "category_distribution": category_counts,
                "gap_categories": list(gap_categories),
                "underrepresented_categories": underrep_categories,
                "published_titles_sample": all_titles[:10]
            }

            self.log_event("Article analysis complete", data=analysis)

            return analysis

        except Exception as e:
            self.log_event(f"Error analyzing articles: {str(e)}", level="ERROR")
            import traceback
            self.log_event(f"Traceback: {traceback.format_exc()}", level="ERROR")
            return {
                "total_articles": 0,
                "category_distribution": {},
                "gap_categories": [],
                "underrepresented_categories": []
            }

    def _select_unique_topic(self, analysis: Dict, published_articles: List[Dict]) -> Dict:
        """
        Select a unique topic that hasn't been covered

        Args:
            analysis: Article analysis results
            published_articles: List of published articles

        Returns:
            Dict with selected topic details
        """
        try:
            # Get published titles for comparison
            published_titles = set([
                article.get('topic_title', '').lower()
                for article in published_articles
                if article.get('topic_title')
            ])

            # Filter out already published topics
            available_topics = [
                topic for topic in TOPIC_BANK
                if topic['title'].lower() not in published_titles
            ]

            if not available_topics:
                self.log_event("All topics published! Using random topic from bank", level="WARNING")
                available_topics = TOPIC_BANK

            # Prioritize gap categories
            gap_categories = analysis.get('gap_categories', [])
            underrep_categories = analysis.get('underrepresented_categories', [])
            priority_categories = set(gap_categories + underrep_categories)

            # Try to find topic in priority categories first
            priority_topics = [
                topic for topic in available_topics
                if topic['category'] in priority_categories
            ]

            if priority_topics:
                selected = random.choice(priority_topics)
                self.log_event(
                    f"Selected priority topic from underrepresented category: {selected['category']}"
                )
            else:
                selected = random.choice(available_topics)
                self.log_event("Selected random available topic")

            # Calculate uniqueness score (simple: 1.0 if not published, 0.5 if reusing)
            # Convert to Decimal for DynamoDB compatibility
            uniqueness_score = Decimal('1.0') if selected['title'].lower() not in published_titles else Decimal('0.5')

            result = {
                "title": selected['title'],
                "keywords": selected['keywords'],
                "category": selected['category'],
                "uniqueness_score": float(uniqueness_score),  # Keep as float for JSON serialization
                "selection_reason": f"Gap category: {selected['category']}" if selected['category'] in priority_categories else "Random selection from available topics"
            }

            self.log_event(f"Topic selected: {result['title']}", data=result)

            return result

        except Exception as e:
            self.log_event(f"Error selecting topic: {str(e)}", level="ERROR")
            # Fallback to random topic
            fallback = random.choice(TOPIC_BANK)
            return {
                "title": fallback['title'],
                "keywords": fallback['keywords'],
                "category": fallback['category'],
                "uniqueness_score": 0.5,
                "selection_reason": "Fallback - error during selection"
            }
