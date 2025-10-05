"""
Optimized Blog Automation Agent for acrossceylon.com
Single-agent approach for budget efficiency (<$100/month)
Handles: Topic selection, research, writing, images, email preview, publishing
"""

import boto3
import json
import requests
import os
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional
import hashlib

# ============================================================================
# CONFIGURATION
# ============================================================================

SANITY_PROJECT_ID = "5xw3644r"
SANITY_DATASET = "blog-production"
SANITY_API_VERSION = "2024-01-01"

# SEO-optimized topic bank - long-tail keywords without number spam
TOPIC_BANK = [
    # Destination-focused cycling content
    {
        "title": "Cycling Through Sri Lanka's Cultural Triangle",
        "keywords": [
            "sri lanka cultural triangle cycling",
            "anuradhapura polonnaruwa bike tour",
            "ancient cities cycling route",
            "sigiriya cycling experience"
        ],
        "category": "Cultural Routes",
    },
    {
        "title": "Hill Country Cycling Adventure Through Ceylon's Tea Estates",
        "keywords": [
            "sri lanka hill country cycling",
            "nuwara eliya bike tour",
            "tea plantation cycling route",
            "ella to kandy cycling"
        ],
        "category": "Hill Country",
    },
    {
        "title": "Coast to Coast: Sri Lanka's Ultimate Cycling Journey",
        "keywords": [
            "coast to coast cycling sri lanka",
            "cross country bike tour",
            "sri lanka cycling holiday",
            "galle to trincomalee cycling"
        ],
        "category": "Epic Routes",
    },
    {
        "title": "Cycling Sri Lanka's Southern Coast and Beaches",
        "keywords": [
            "south coast cycling sri lanka",
            "galle mirissa bike route",
            "beach cycling holiday",
            "coastal cycling tour"
        ],
        "category": "Coastal Routes",
    },
    {
        "title": "Knuckles Mountain Range: Sri Lanka's Premier Cycling Challenge",
        "keywords": [
            "knuckles mountain range cycling",
            "mountain biking sri lanka",
            "challenging cycling routes",
            "knuckles bike tour"
        ],
        "category": "Mountain Biking",
    },
    {
        "title": "Wildlife Cycling Safari: Yala to Udawalawe Adventure",
        "keywords": [
            "wildlife cycling sri lanka",
            "yala national park bike tour",
            "elephant cycling safari",
            "udawalawe cycling route"
        ],
        "category": "Wildlife",
    },
    {
        "title": "Cycling Sri Lanka: Complete Planning Guide for First-Timers",
        "keywords": [
            "cycling sri lanka guide",
            "plan bike tour sri lanka",
            "sri lanka cycling tips",
            "bike holiday planning"
        ],
        "category": "Planning",
    },
    {
        "title": "When to Cycle Sri Lanka: Seasonal Guide and Weather Patterns",
        "keywords": [
            "best time cycling sri lanka",
            "sri lanka cycling season",
            "monsoon cycling routes",
            "dry season bike tours"
        ],
        "category": "Planning",
    },
    {
        "title": "Gravel Cycling Adventures in Rural Sri Lanka",
        "keywords": [
            "gravel biking sri lanka",
            "gravel cycling routes",
            "rural cycling adventures",
            "off-road bike tours"
        ],
        "category": "Adventure",
    },
    {
        "title": "Cycling Through Sri Lanka's Spice Gardens and Plantations",
        "keywords": [
            "spice garden cycling tour",
            "cinnamon plantation cycling",
            "agricultural cycling routes",
            "farm to table bike tour"
        ],
        "category": "Cultural Experience",
    },
    {
        "title": "Family Cycling Holidays in Sri Lanka: Safe Routes and Activities",
        "keywords": [
            "family cycling sri lanka",
            "kid friendly bike tours",
            "safe cycling routes families",
            "family bike holiday asia"
        ],
        "category": "Family Travel",
    },
    {
        "title": "E-Bike Tours: Exploring Sri Lanka Without Breaking a Sweat",
        "keywords": [
            "e-bike tours sri lanka",
            "electric bicycle touring",
            "assisted cycling holiday",
            "ebike rental sri lanka"
        ],
        "category": "E-Bike",
    },
    {
        "title": "Cycling and Yoga Retreats: Wellness in Sri Lanka",
        "keywords": [
            "cycling yoga retreat sri lanka",
            "wellness bike tour",
            "active meditation holiday",
            "mindful cycling vacation"
        ],
        "category": "Wellness",
    },
    {
        "title": "Cycling Sri Lanka's Coffee Triangle: From Bean to Cup",
        "keywords": [
            "coffee cycling tour sri lanka",
            "coffee plantation bike route",
            "specialty coffee cycling",
            "haputale cycling experience"
        ],
        "category": "Culinary",
    },
    {
        "title": "Multi-Day Cycling Expeditions Across Sri Lanka",
        "keywords": [
            "multi day cycling tour sri lanka",
            "week long bike expedition",
            "cycling expedition asia",
            "supported bike tour sri lanka"
        ],
        "category": "Epic Routes",
    },
    {
        "title": "Cycling Safety and Road Conditions in Sri Lanka",
        "keywords": [
            "cycling safety sri lanka",
            "road conditions bike touring",
            "safe cycling tips asia",
            "sri lanka traffic cycling"
        ],
        "category": "Safety",
    },
    {
        "title": "Solo Cycling in Sri Lanka: Independent Travel Guide",
        "keywords": [
            "solo cycling sri lanka",
            "independent bike tour",
            "self guided cycling route",
            "solo traveler bike holiday"
        ],
        "category": "Solo Travel",
    },
    {
        "title": "Cycling and Wildlife Photography Safari in Sri Lanka",
        "keywords": [
            "wildlife photography cycling",
            "bike safari sri lanka",
            "photography tour cycling",
            "leopard spotting bike tour"
        ],
        "category": "Photography",
    },
    {
        "title": "Budget-Friendly Cycling Tours and Backroads of Sri Lanka",
        "keywords": [
            "budget cycling tour sri lanka",
            "cheap bike holiday",
            "backpacker cycling route",
            "affordable bike tours asia"
        ],
        "category": "Budget Travel",
    },
    {
        "title": "Luxury Cycling Holidays: Five-Star Tours of Sri Lanka",
        "keywords": [
            "luxury cycling tour sri lanka",
            "high end bike holiday",
            "boutique cycling experience",
            "premium bike tour asia"
        ],
        "category": "Luxury",
    },
    {
        "title": "Cycling Through Sri Lanka's Rice Paddies and Farming Villages",
        "keywords": [
            "rice paddy cycling tour",
            "rural village bike route",
            "agricultural cycling sri lanka",
            "farming community tours"
        ],
        "category": "Rural Routes",
    },
    {
        "title": "Cycling the Adam's Peak Pilgrimage Route",
        "keywords": [
            "adams peak cycling route",
            "pilgrimage bike tour",
            "sacred mountain cycling",
            "sri pada bike adventure"
        ],
        "category": "Cultural Routes",
    },
    {
        "title": "Night Sky Cycling: Stargazing Tours in Rural Sri Lanka",
        "keywords": [
            "night cycling sri lanka",
            "stargazing bike tour",
            "moonlight cycling experience",
            "astronomy cycling holiday"
        ],
        "category": "Unique Experiences",
    },
    {
        "title": "Cycling and Ayurveda: Holistic Wellness Tours",
        "keywords": [
            "ayurveda cycling retreat",
            "wellness bike tour sri lanka",
            "holistic cycling holiday",
            "ayurvedic spa cycling"
        ],
        "category": "Wellness",
    },
]


# ============================================================================
# UNIFIED BLOG AGENT
# ============================================================================


class BlogAgent:
    """Single intelligent agent for complete blog automation"""

    def __init__(self):
        from botocore.config import Config

        # Configure Bedrock with longer timeout for article generation
        bedrock_config = Config(
            read_timeout=300,  # 5 minutes
            connect_timeout=60,
            retries={'max_attempts': 3}
        )

        self.bedrock = boto3.client("bedrock-runtime", region_name="us-east-1", config=bedrock_config)
        self.dynamodb = boto3.resource("dynamodb", region_name="us-east-1")
        self.ses = boto3.client("ses", region_name="us-east-1")
        self.secrets = boto3.client("secretsmanager", region_name="us-east-1")
        self.cloudwatch = boto3.client("cloudwatch", region_name="us-east-1")

        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        # Load secrets
        self.sanity_token = self._get_secret("blog-sanity-token")["token"]
        self.pexels_key = self._get_secret("blog-pexels-key")["key"]

        # Load Cloudinary credentials (optional)
        try:
            cloudinary_secret = self._get_secret("blog-cloudinary-credentials")
            self.cloudinary_cloud_name = cloudinary_secret.get("cloud_name")
            self.cloudinary_api_key = cloudinary_secret.get("api_key")
            self.cloudinary_api_secret = cloudinary_secret.get("api_secret")
        except:
            self.cloudinary_cloud_name = None
            print("Cloudinary credentials not found, using Pexels only")

        # Load Google Ads API credentials (optional - for keyword research)
        try:
            google_ads_secret = self._get_secret("blog-google-ads-credentials")
            self.google_ads_client_id = google_ads_secret.get("client_id")
            self.google_ads_client_secret = google_ads_secret.get("client_secret")
            # Note: You'll also need refresh_token and developer_token for full API access
            self.google_ads_refresh_token = google_ads_secret.get("refresh_token")
            self.google_ads_developer_token = google_ads_secret.get("developer_token")
        except:
            self.google_ads_client_id = None
            print("Google Ads API credentials not found, using static keywords")

        # DynamoDB table
        self.workflow_table = self.dynamodb.Table("blog-workflow-state")

        # Sanity API
        self.sanity_base_url = (
            f"https://{SANITY_PROJECT_ID}.api.sanity.io/v{SANITY_API_VERSION}"
        )
        self.sanity_headers = {
            "Authorization": f"Bearer {self.sanity_token}",
            "Content-Type": "application/json",
        }

    def _get_secret(self, secret_name: str) -> Dict:
        """Retrieve secret from AWS Secrets Manager"""
        try:
            response = self.secrets.get_secret_value(SecretId=secret_name)
            return json.loads(response["SecretString"])
        except Exception as e:
            raise Exception(f"Failed to retrieve {secret_name}: {str(e)}")

    def _publish_metric(self, metric_name: str, value: float, unit: str = "None", dimensions: Dict = None):
        """Publish metric to CloudWatch"""
        try:
            metric_data = {
                "MetricName": metric_name,
                "Value": value,
                "Unit": unit,
                "Timestamp": datetime.now(timezone.utc)
            }

            if dimensions:
                metric_data["Dimensions"] = [
                    {"Name": k, "Value": str(v)} for k, v in dimensions.items()
                ]

            self.cloudwatch.put_metric_data(
                Namespace="BlogAutomation",
                MetricData=[metric_data]
            )
        except Exception as e:
            print(f"Warning: Failed to publish metric {metric_name}: {str(e)}")

    def select_next_topic(self) -> Dict:
        """Select next topic from bank based on what hasn't been used"""
        try:
            response = self.workflow_table.scan(
                FilterExpression="attribute_exists(published_date)",
                ProjectionExpression="topic_title",
            )
            used_titles = {
                item.get("topic_title") for item in response.get("Items", [])
            }
        except:
            used_titles = set()

        available = [t for t in TOPIC_BANK if t["title"] not in used_titles]
        if not available:
            available = TOPIC_BANK

        return available[0]

    def _get_recent_articles(self) -> List[str]:
        """Get summaries of recently published articles to avoid repetition"""
        try:
            # Get last 5 published articles from DynamoDB
            response = self.workflow_table.scan(
                FilterExpression="attribute_exists(published_date)",
                ProjectionExpression="article_data, published_date",
                Limit=10
            )

            articles = []
            for item in response.get("Items", []):
                try:
                    article_data = json.loads(item.get("article_data", "{}"))
                    title = article_data.get("title", "")
                    content_preview = article_data.get("content", "")[:300]
                    articles.append(f"- {title}: {content_preview}...")
                except:
                    continue

            return articles[-5:]  # Last 5 articles
        except Exception as e:
            print(f"Error fetching recent articles: {str(e)}")
            return []

    def _get_trending_keywords(self, topic: Dict) -> List[str]:
        """Fetch trending keywords from Google Keyword Planner API"""
        if not self.google_ads_client_id or not self.google_ads_refresh_token:
            print("Google Ads API not fully configured, using static keywords")
            return topic.get("keywords", [])

        try:
            # Get OAuth2 access token
            token_response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.google_ads_client_id,
                    "client_secret": self.google_ads_client_secret,
                    "refresh_token": self.google_ads_refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )

            if token_response.status_code != 200:
                print(f"OAuth2 token error: {token_response.text}")
                return topic.get("keywords", [])

            access_token = token_response.json().get("access_token")

            # Use Google Ads API to get keyword ideas
            # Note: This requires google-ads library, simplified version here
            headers = {
                "Authorization": f"Bearer {access_token}",
                "developer-token": self.google_ads_developer_token,
                "Content-Type": "application/json"
            }

            # Simplified keyword request (actual API is more complex)
            base_keywords = topic.get("keywords", [])[:2]
            keyword_ideas = []

            for keyword in base_keywords:
                # This is a simplified version - real implementation needs google-ads library
                print(f"Fetching keyword ideas for: {keyword}")
                keyword_ideas.append(keyword)

            # Merge with existing keywords
            all_keywords = list(set(topic.get("keywords", []) + keyword_ideas))
            return all_keywords[:6]  # Return top 6 keywords

        except Exception as e:
            print(f"Error fetching trending keywords: {str(e)}")
            return topic.get("keywords", [])

    def research_and_write(self, topic: Dict) -> Dict:
        """Combined research and writing in single Claude call"""

        # Get trending keywords from Google Ads API
        trending_keywords = self._get_trending_keywords(topic)
        print(f"Using keywords: {trending_keywords}")

        # Get recent articles to avoid repetition
        recent_articles = self._get_recent_articles()
        recent_context = ""
        if recent_articles:
            recent_context = f"""

CRITICAL - AVOID REPETITION:
We have recently published these articles. Your new article MUST be completely different in:
- Writing style and tone variations
- Different route selections and angles
- Unique cultural insights and stories
- Fresh metaphors and descriptions (don't reuse phrases from these)
- Different seasonal/festival references
- Varied practical tips

Recent articles:
{chr(10).join(recent_articles)}

DO NOT repeat similar structures, phrases, or content patterns from above articles.
"""

        prompt = f"""You are an expert travel writer for Across Ceylon (acrossceylon.com), Asia's premier cycling tour operator specializing in Sri Lanka.

Write an exceptional, SEO-optimized blog article on: {topic['title']}
Primary Keywords (integrate naturally): {', '.join(trending_keywords)}
Category: {topic['category']}
{recent_context}
CRITICAL: Output as Sanity Portable Text JSON format (NOT markdown).

WRITING EXCELLENCE:
- Create compelling, imaginative titles that go beyond simple lists (avoid generic "10 Most..." - use creative angles like "Pedal Through Paradise", "Two Wheels Through Time", "Ceylon's Hidden Cycling Gems", "The Ultimate Cycling Odyssey")
- Position Sri Lanka as Asia's premier cycling destination alongside Europe's best
- Weave in Sri Lanka's unique selling points: 2,500+ years of history, 8 UNESCO World Heritage Sites, diverse ecosystems from beaches to mountains within hours
- Include seasonal insights (monsoon seasons, dry season advantages), local festivals (Vesak, Kandy Esala Perahera), regional cuisine
- Reference Across Ceylon's expertise as Sri Lanka's leading cycling tour operator with 10+ years experience
- Paint vivid pictures with sensory details: monsoon mists, spice-scented air, temple bells, ocean breezes, jungle sounds
- Balance adventure with cultural immersion and wildlife encounters
- Use superlatives naturally: "Asia's best", "world-renowned", "legendary", "unparalleled"

INTERNAL LINKING (Must include 2-3 natural links):
Add links to Across Ceylon pages within your content. Example for a linked span:
{{
    "children": [
        {{"_type": "span", "_key": "span1a", "text": "Experience our ", "marks": []}},
        {{"_type": "span", "_key": "span1b", "text": "Coast to Coast adventure", "marks": ["link1"]}},
        {{"_type": "span", "_key": "span1c", "text": " for the ultimate journey.", "marks": []}}
    ],
    "markDefs": [
        {{"_type": "link", "_key": "link1", "href": "https://acrossceylon.com/acrossceylon-package/coast-to-coast/"}}
    ]
}}

Link these pages naturally:
- Premium packages: https://acrossceylon.com/acrossceylon-package/across-ceylon-pro/, https://acrossceylon.com/acrossceylon-package/coast-to-coast/
- Signature routes: https://acrossceylon.com/acrossceylon-routes/across-kingdoms/, https://acrossceylon.com/acrossceylon-routes/wild-ceylon/
- About: https://acrossceylon.com/about-us/

STRUCTURE:
- H1 creative, SEO-optimized title (55-60 chars max)
- Engaging introduction (150-200 words) establishing Sri Lanka as world-class cycling destination
- 8-10 main sections with creative H2 headers (can be routes, experiences, regions, or themed sections)
- Each section: rich description (250-350 words), highlights as bullet lists, practical insights, cultural context
- Conclusion with strong call-to-action mentioning Across Ceylon's expertise
- Target 2500-3500 words

CRITICAL FORMATTING RULES:
- DO NOT use markdown syntax (no ###, ##, **, -, etc)
- Output ONLY valid Portable Text JSON blocks
- Section headers MUST be style: "h2" blocks
- Bullet points must use "listItem": "bullet" property
- Include 2-3 internal links using marks and markDefs

Return ONLY valid JSON (no code blocks, no markdown formatting):

{{
    "title": "Article title (max 60 chars, SEO-optimized)",
    "portable_text_body": [
        {{
            "_key": "key1",
            "_type": "block",
            "style": "h1",
            "children": [{{"_type": "span", "_key": "span1", "text": "Main Title Here", "marks": []}}],
            "markDefs": []
        }},
        {{
            "_key": "key2",
            "_type": "block",
            "style": "normal",
            "children": [{{"_type": "span", "_key": "span2", "text": "Introduction paragraph with Pearl of the Indian Ocean theme and vivid descriptions.", "marks": []}}],
            "markDefs": []
        }},
        {{
            "_key": "key3",
            "_type": "block",
            "style": "h2",
            "children": [{{"_type": "span", "_key": "span3", "text": "1. First Cycling Route Name", "marks": []}}],
            "markDefs": []
        }},
        {{
            "_key": "key4",
            "_type": "block",
            "style": "normal",
            "children": [
                {{"_type": "span", "_key": "span4a", "text": "Description with ", "marks": []}},
                {{"_type": "span", "_key": "span4b", "text": "bold highlights", "marks": ["strong"]}},
                {{"_type": "span", "_key": "span4c", "text": " and details.", "marks": []}}
            ],
            "markDefs": []
        }},
        {{
            "_key": "key5",
            "_type": "block",
            "style": "normal",
            "children": [{{"_type": "span", "_key": "span5", "text": "Highlights:", "marks": ["strong"]}}],
            "markDefs": []
        }},
        {{
            "_key": "key6",
            "_type": "block",
            "style": "normal",
            "listItem": "bullet",
            "level": 1,
            "children": [{{"_type": "span", "_key": "span6", "text": "First highlight point", "marks": []}}],
            "markDefs": []
        }},
        {{
            "_key": "key7",
            "_type": "block",
            "style": "normal",
            "listItem": "bullet",
            "level": 1,
            "children": [{{"_type": "span", "_key": "span7", "text": "Second highlight point", "marks": []}}],
            "markDefs": []
        }}
    ],
    "seo_metadata": {{
        "meta_title": "SEO title (max 60 chars)",
        "meta_description": "Compelling description (140-160 chars) with primary keyword",
        "keywords": ["keyword1", "keyword2", "keyword3"]
    }},
    "image_search_terms": ["sri lanka cycling", "tea plantations", "coastal cycling"]
}}

IMPORTANT:
- Generate unique _key values (key1, key2, key3... and span1, span2, span3...)
- For bullet lists: use "listItem": "bullet", "level": 1
- For bold text: use "marks": ["strong"]
- Include 10 route sections with H2 headers
- Each route needs description + highlights + practical tips
- Write complete article now in this exact JSON format."""

        try:
            response = self.bedrock.invoke_model(
                modelId=self.model_id,
                body=json.dumps(
                    {
                        "anthropic_version": "bedrock-2023-05-31",
                        "max_tokens": 16000,  # Increased for full Portable Text JSON output
                        "temperature": 0.7,
                        "messages": [{"role": "user", "content": prompt}],
                    }
                ),
            )

            result = json.loads(response["body"].read())
            content_text = result["content"][0]["text"]

            # Debug logging
            print("=" * 50)
            print("RAW CLAUDE RESPONSE (first 500 chars):")
            print(repr(content_text[:500]))
            print("=" * 50)

            article = self._extract_json(content_text)

            # Derive plain text content if missing (for preview & counts)
            if "content" not in article:
                if "portable_text_body" in article:
                    parts = []
                    for block in article["portable_text_body"]:
                        if block.get("_type") == "block":
                            spans = [c.get("text", "") for c in block.get("children", [])]
                            parts.append("".join(spans))
                    article["content"] = "\n\n".join(parts)
                else:
                    article["content"] = ""

            # Add word count & reading time if absent
            if "word_count" not in article:
                article["word_count"] = len(article["content"].split())
            if "reading_time" not in article:
                article["reading_time"] = max(1, article["word_count"] // 200)

            article["original_topic"] = topic
            return article

        except Exception as e:
            print(f"Error in research_and_write: {str(e)}")
            raise

    def _extract_json(self, text: str) -> Dict:
        """Extract JSON from Claude's response"""
        import re

        print(f"_extract_json called with text length: {len(text)}")
        print(f"First 100 chars of input: {repr(text[:100])}")

        try:
            # Remove markdown code blocks if present
            if '```json' in text:
                start = text.find('```json') + 7
                end = text.find('```', start)
                json_str = text[start:end].strip()
                print(f"Extracted from ```json block")
            elif '```' in text:
                start = text.find('```') + 3
                end = text.find('```', start)
                json_str = text[start:end].strip()
                print(f"Extracted from ``` block")
            else:
                # The entire response should be JSON - just use it directly
                json_str = text.strip()
                print(f"Using entire text as JSON")

            print(f"Extracted JSON string length: {len(json_str)}")
            print(f"First 100 chars: {repr(json_str[:100])}")
            print(f"Last 100 chars: {repr(json_str[-100:])}")

            # Try parsing first
            try:
                parsed = json.loads(json_str)
                print(f"Successfully parsed JSON with keys: {parsed.keys()}")
                return parsed
            except json.JSONDecodeError as e:
                print(f"Initial JSON parse failed at position {e.pos}: {str(e)}")
                print(f"Context around error: ...{json_str[max(0, e.pos-50):e.pos+50]}...")

                # Try fixing common issues
                # 1. Remove any control characters
                json_str_fixed = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', json_str)

                # 2. Try again
                parsed = json.loads(json_str_fixed)
                print(f"Successfully parsed JSON after cleanup with keys: {parsed.keys()}")
                return parsed

        except json.JSONDecodeError as e:
            print(f"JSON decode error (final): {e}")
            print(f"Error position: {e.pos if hasattr(e, 'pos') else 'unknown'}")
            if 'json_str' in locals() and hasattr(e, 'pos'):
                error_context_start = max(0, e.pos - 100)
                error_context_end = min(len(json_str), e.pos + 100)
                print(f"Context around error position {e.pos}:")
                print(f"...{json_str[error_context_start:error_context_end]}...")

            # Return a minimal valid structure
            return {
                "title": "Error parsing article",
                "portable_text_body": [],
                "content": "Article generation failed",
                "seo_metadata": {
                    "meta_title": "Error",
                    "meta_description": "Error generating article",
                    "keywords": ["error"]
                },
                "image_search_terms": ["sri lanka", "cycling", "landscape"],
                "word_count": 0,
                "reading_time": 0
            }
        except Exception as e:
            print(f"Unexpected error extracting JSON: {str(e)}")
            return {
                "title": "Error parsing article",
                "portable_text_body": [],
                "content": "Article generation failed",
                "seo_metadata": {
                    "meta_title": "Error",
                    "meta_description": "Error generating article",
                    "keywords": ["error"]
                },
                "image_search_terms": ["sri lanka", "cycling", "landscape"],
                "word_count": 0,
                "reading_time": 0
            }

    def find_images(self, article: Dict) -> List[Dict]:
        """Find relevant images from Cloudinary and Pexels"""
        images = []
        search_terms = article.get("image_search_terms", [])[:3]

        # First, try to get images from Cloudinary if configured
        if self.cloudinary_cloud_name:
            try:
                cloudinary_images = self._fetch_cloudinary_images(search_terms)
                images.extend(cloudinary_images)
                print(f"Added {len(cloudinary_images)} images from Cloudinary")
            except Exception as e:
                print(f"Error fetching Cloudinary images: {str(e)}")

        # Fill remaining slots with Pexels images
        for term in search_terms:
            if len(images) >= 5:
                break

            try:
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
                    data = response.json()
                    for photo in data.get("photos", []):
                        if len(images) >= 5:
                            break
                        images.append(
                            {
                                "url": photo["src"]["large"],
                                "alt": f"{term} in Sri Lanka - cycling destination",
                                "credit": f"Photo by {photo['photographer']} from Pexels",
                                "credit_url": photo["photographer_url"],
                            }
                        )
            except Exception as e:
                print(f"Error fetching Pexels images for {term}: {str(e)}")
                continue

        return images

    def _fetch_cloudinary_images(self, search_terms: List[str]) -> List[Dict]:
        """Fetch images from Cloudinary based on tags/folder"""
        images = []

        try:
            # List all images (without folder prefix to get everything)
            response = requests.get(
                f"https://api.cloudinary.com/v1_1/{self.cloudinary_cloud_name}/resources/image",
                params={
                    "type": "upload",
                    "max_results": 30,  # Get more to randomize selection
                },
                auth=(self.cloudinary_api_key, self.cloudinary_api_secret),
                timeout=10
            )

            print(f"Cloudinary API response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                resources = data.get("resources", [])
                print(f"Found {len(resources)} images in Cloudinary")

                # Randomly select 3 images to add variety
                import random
                selected = random.sample(resources, min(3, len(resources)))

                for resource in selected:
                    public_id = resource.get("public_id")
                    print(f"Adding Cloudinary image: {public_id}")
                    images.append({
                        "url": f"https://res.cloudinary.com/{self.cloudinary_cloud_name}/image/upload/w_1200,q_auto,f_auto/{public_id}",
                        "alt": "Cycling in Sri Lanka - Across Ceylon",
                        "credit": "Photo by Across Ceylon",
                        "credit_url": "https://acrossceylon.com",
                    })
            else:
                print(f"Cloudinary API error response: {response.text}")

        except Exception as e:
            print(f"Cloudinary API error: {str(e)}")
            import traceback
            traceback.print_exc()

        return images

    def send_email_preview(
        self, article: Dict, images: List[Dict], workflow_id: str
    ) -> bool:
        """Send email preview with approve/decline links"""
        approval_token = self._generate_token(workflow_id)

        self.workflow_table.put_item(
            Item={
                "workflow_id": workflow_id,
                "status": "awaiting_approval",
                "article_data": json.dumps(article),
                "images_data": json.dumps(images),
                "approval_token": approval_token,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "topic_title": article["title"],
            }
        )

        api_url = os.environ.get("API_GATEWAY_URL", "YOUR_API_URL")
        preview_text = article["content"][:800] + "..."

        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 700px; margin: 0 auto; padding: 20px; }}
                .header {{ background: #2c5282; color: white; padding: 20px; text-align: center; }}
                .metadata {{ background: #f7fafc; padding: 15px; margin: 20px 0; border-left: 4px solid #4299e1; }}
                .content {{ line-height: 1.6; padding: 20px 0; }}
                .actions {{ text-align: center; margin: 30px 0; }}
                .btn {{ display: inline-block; padding: 15px 30px; margin: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .btn-approve {{ background: #48bb78; color: white; }}
                .btn-decline {{ background: #f56565; color: white; }}
                .images {{ margin: 20px 0; }}
                .images img {{ max-width: 200px; margin: 10px; border-radius: 8px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>📝 New Article Ready for Review</h1>
            </div>
            <h2>{article['title']}</h2>
            <div class="metadata">
                <p><strong>📊 Word Count:</strong> {article['word_count']}</p>
                <p><strong>⏱️ Reading Time:</strong> {article['reading_time']} minutes</p>
                <p><strong>🔑 Keywords:</strong> {', '.join(article['seo_metadata']['keywords'])}</p>
                <p><strong>📁 Category:</strong> {article['original_topic']['category']}</p>
            </div>
            <div class="content">
                <h3>Article Preview:</h3>
                <p>{preview_text}</p>
                <p><em>... (full article will be published)</em></p>
            </div>
            <div class="images">
                <h3>Images ({len(images)}):</h3>
                {''.join([f'<img src="{img["url"]}" alt="{img["alt"]}">' for img in images[:3]])}
            </div>
            <div class="actions">
                <a href="{api_url}/approve?token={approval_token}&action=approve" class="btn btn-approve">
                    ✅ APPROVE & PUBLISH
                </a>
                <a href="{api_url}/approve?token={approval_token}&action=decline" class="btn btn-decline">
                    ❌ DECLINE
                </a>
            </div>
            <p style="text-align: center; color: #666; font-size: 12px; margin-top: 40px;">
                This article was generated automatically by your blog automation system.<br>
                Workflow ID: {workflow_id}
            </p>
        </body>
        </html>
        """

        try:
            response = self.ses.send_email(
                Source="chin@acrossceylon.com",
                Destination={"ToAddresses": ["chin@acrossceylon.com"]},
                Message={
                    "Subject": {"Data": f'New Article: {article["title"][:50]}...'},
                    "Body": {"Html": {"Data": html_body}},
                },
            )
            print(f"Email sent: {response['MessageId']}")
            return True
        except Exception as e:
            print(f"Error sending email: {str(e)}")
            return False

    def _generate_token(self, workflow_id: str) -> str:
        """Generate secure approval token"""
        data = f"{workflow_id}:{datetime.now().isoformat()}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]

    def publish_to_sanity(self, article: Dict, images: List[Dict]) -> Dict:
        """Publish article to Sanity CMS"""
        author_id = self._get_or_create_author()

        sanity_images = []
        for img in images:
            try:
                sanity_img = self._upload_image_to_sanity(img["url"], img["alt"])
                sanity_images.append(sanity_img)
            except Exception as e:
                print(f"Error uploading image: {str(e)}")
                continue

        # Use portable_text_body directly from Claude
        body = article.get("portable_text_body", [])

        # Debug logging
        print(f"Article keys: {article.keys()}")
        print(f"Body blocks count: {len(body)}")
        if len(body) == 0:
            print("WARNING: Empty body! Article data:")
            print(json.dumps(article, indent=2)[:500])

        # Insert images every 15 blocks
        image_index = 0
        for i in range(15, len(body), 15):
            if image_index < len(sanity_images):
                import uuid
                body.insert(i, {
                    "_type": "image",
                    "_key": str(uuid.uuid4()).replace('-', '')[:12],
                    **sanity_images[image_index],
                    "loading": "lazy"
                })
                image_index += 1
        category_refs = []
        categories_to_use = [article["original_topic"]["category"]]

        for cat_name in categories_to_use:
            cat_id = self._get_or_create_category(cat_name)
            category_refs.append({"_type": "reference", "_ref": cat_id, "_key": cat_id})

        slug = self._generate_slug(article["title"])

        # Format date as yyyy-mm-dd
        publish_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        article_doc = {
            "_type": "blog.post",
            "body": body,
            "categories": category_refs,
            "authors": [{"_type": "reference", "_ref": author_id, "_key": author_id}],
            "publishDate": publish_date,
            "featured": False,
            "hideTableOfContents": False,
            "metadata": {
                "_type": "metadata",
                "slug": {"_type": "slug", "current": slug},
                "title": article["seo_metadata"]["meta_title"][:60],
                "description": article["seo_metadata"]["meta_description"][:160],
            },
        }

        if sanity_images:
            article_doc["metadata"]["image"] = sanity_images[0]
        
        print("=" * 50)
        print("BODY SENT TO SANITY (first 5 blocks):")
        print(json.dumps(body[:5], indent=2))
        print("=" * 50)

        mutation = {"mutations": [{"create": article_doc}]}

        response = requests.post(
            f"{self.sanity_base_url}/data/mutate/{SANITY_DATASET}",
            headers=self.sanity_headers,
            json=mutation
        )
        print(f"Category creation response: {response.status_code}")
        print(f"Response body: {response.text}")
        
        if response.status_code == 200:
            result_data = response.json()
            print(f"Sanity response: {json.dumps(result_data)}")
            
            # Handle different Sanity response formats
            if 'results' in result_data and len(result_data['results']) > 0:
                result = result_data['results'][0]
                # Try different possible ID fields
                doc_id = result.get('id') or result.get('_id') or result.get('documentId', 'unknown')
            else:
                doc_id = 'unknown'
            
            return {
                "success": True,
                "document_id": doc_id,
                "slug": slug,
                "url": f"https://blog.acrossceylon.com/blog/{slug}"
            }
        else:
            error_msg = f"Publishing failed: {response.status_code} - {response.text}"
            print(error_msg)
            raise Exception(error_msg)

    def _get_or_create_author(self) -> str:
        """Get or create default author"""
        
        # Query for existing author
        query = '*[_type == "person"][0]'
        query_url = f"{self.sanity_base_url}/data/query/{SANITY_DATASET}?query={query}"
        
        response = requests.get(query_url, headers=self.sanity_headers)
        result = response.json().get('result')
        
        if result:
            return result['_id']
        
        # Generate a unique ID for the new author
        import uuid
        author_id = f"person-{uuid.uuid4().hex[:16]}"
        
        # Create new author with explicit ID
        author_doc = {
            "_id": author_id,
            "_type": "person",
            "name": "Across Ceylon Team",
            "slug": {
                "_type": "slug",
                "current": "across-ceylon-team"
            }
        }
        
        mutation = {
            "mutations": [{
                "createOrReplace": author_doc
            }]
        }
        
        response = requests.post(
            f"{self.sanity_base_url}/data/mutate/{SANITY_DATASET}",
            headers=self.sanity_headers,
            json=mutation
        )
        
        if response.status_code == 200:
            return author_id
        else:
            raise Exception(f"Author creation failed: {response.text}")
    def _get_or_create_category(self, category_name: str) -> str:
        """Get existing category or create new one"""
        
        slug = self._generate_slug(category_name)
        
        # Query for existing category - use proper GROQ syntax
        query = f'*[_type == "blog.category" && slug.current == "{slug}"]{{_id, title}}[0]'
        query_url = f"{self.sanity_base_url}/data/query/{SANITY_DATASET}"
        
        response = requests.get(
            query_url,
            headers=self.sanity_headers,
            params={'query': query}
        )
        
        result = response.json().get('result')
        
        if result and '_id' in result:
            print(f"Found existing category: {result['_id']}")
            return result['_id']
        
        # Create with UUID
        import uuid
        category_id = f"category-{uuid.uuid4().hex[:16]}"
        
        category_doc = {
            "_id": category_id,
            "_type": "blog.category",
            "title": category_name,
            "slug": {
                "_type": "slug",
                "current": slug
            }
        }
        
        mutation = {"mutations": [{"createOrReplace": category_doc}]}
        
        response = requests.post(
            f"{self.sanity_base_url}/data/mutate/{SANITY_DATASET}",
            headers=self.sanity_headers,
            json=mutation
        )
        
        if response.status_code == 200:
            print(f"Created new category: {category_id}")
            return category_id
        else:
            raise Exception(f"Category creation failed: {response.text}")


    def _upload_image_to_sanity(self, image_url: str, alt_text: str) -> Dict:
        """Upload image to Sanity CDN"""
        img_response = requests.get(image_url, timeout=10)
        img_data = img_response.content

        upload_url = f"{self.sanity_base_url}/assets/images/{SANITY_DATASET}"

        upload_response = requests.post(
            upload_url,
            headers={"Authorization": f"Bearer {self.sanity_token}"},
            data=img_data,
        )

        if upload_response.status_code == 200:
            asset_data = upload_response.json()
            return {
                "_type": "image",
                "asset": {"_type": "reference", "_ref": asset_data["document"]["_id"]},
                "alt": alt_text,
            }
        else:
            raise Exception(f"Image upload failed: {upload_response.text}")

    def _markdown_to_portable_text(self, markdown: str, images: List[Dict]) -> List[Dict]:
        """Convert markdown to Sanity Portable Text matching exact schema"""
        import uuid
        # CRITICAL FIX: Handle escaped newlines
        if '\\n' in markdown:
            markdown = markdown.replace('\\n', '\n') 
        # Also handle potential other escape sequences
        markdown = markdown.replace('\\r', '').replace('\r', '')
        print(f"Processing markdown with {len(markdown)} chars")
        print(f"First 200 chars: {markdown[:200]}")      
        portable_text = []
        lines = markdown.split('\n')
        print(f"Split into {len(lines)} lines")      
        image_index = 0
        paragraph_count = 0
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line:
                i += 1
                continue
            
            # Generate unique key
            block_key = str(uuid.uuid4()).replace('-', '')[:12]
            
            # H3 headers
            if line.startswith('### '):
                portable_text.append({
                    "_type": "block",
                    "_key": block_key,
                    "style": "h3",
                    "children": [{
                        "_type": "span",
                        "_key": str(uuid.uuid4()).replace('-', '')[:12],
                        "text": line[4:],
                        "marks": []
                    }],
                    "markDefs": []
                })
            # H2 headers
            elif line.startswith('## '):
                portable_text.append({
                    "_type": "block",
                    "_key": block_key,
                    "style": "h2",
                    "children": [{
                        "_type": "span",
                        "_key": str(uuid.uuid4()).replace('-', '')[:12],
                        "text": line[3:],
                        "marks": []
                    }],
                    "markDefs": []
                })
            # Bullet lists
            elif line.startswith('- '):
                while i < len(lines) and lines[i].strip().startswith('- '):
                    item_key = str(uuid.uuid4()).replace('-', '')[:12]
                    portable_text.append({
                        "_type": "block",
                        "_key": item_key,
                        "style": "normal",
                        "listItem": "bullet",
                        "level": 1,
                        "children": [{
                            "_type": "span",
                            "_key": str(uuid.uuid4()).replace('-', '')[:12],
                            "text": lines[i].strip()[2:],
                            "marks": []
                        }],
                        "markDefs": []
                    })
                    i += 1
                i -= 1
            # Normal paragraphs
            else:
                portable_text.append({
                    "_type": "block",
                    "_key": block_key,
                    "style": "normal",
                    "children": [{
                        "_type": "span",
                        "_key": str(uuid.uuid4()).replace('-', '')[:12],
                        "text": line,
                        "marks": []
                    }],
                    "markDefs": []
                })
                paragraph_count += 1
            
            # Insert image every 5 paragraphs
            if paragraph_count > 0 and paragraph_count % 5 == 0 and image_index < len(images):
                img_key = str(uuid.uuid4()).replace('-', '')[:12]
                portable_text.append({
                    "_type": "image",
                    "_key": img_key,
                    **images[image_index],
                    "loading": "lazy"
                })
                image_index += 1
            
            i += 1
        
# Debug: print first 3 blocks to see structure
        print(f"Generated {len(portable_text)} blocks")
        if len(portable_text) > 0:
            print(f"First block: {json.dumps(portable_text[0], indent=2)}")
        if len(portable_text) > 1:
            print(f"Second block: {json.dumps(portable_text[1], indent=2)}")
        
        return portable_text



    def _generate_slug(self, title: str) -> str:
        """Generate URL-friendly slug"""
        slug = title.lower()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[-\s]+", "-", slug)
        return slug.strip("-")[:50]


# ============================================================================
# LAMBDA HANDLERS
# ============================================================================


def daily_workflow_handler(event, context):
    """Main handler - triggered daily by EventBridge"""
    agent = BlogAgent()
    workflow_id = f"workflow-{int(datetime.now().timestamp())}"

    try:
        print("Starting daily workflow...")
        topic = agent.select_next_topic()
        print(f"Selected topic: {topic['title']}")

        print("Researching and writing article...")
        article = agent.research_and_write(topic)
        print(f"Article completed: {article['word_count']} words")

        print("Finding images...")
        images = agent.find_images(article)
        print(f"Found {len(images)} images")

        print("Sending email preview...")
        email_sent = agent.send_email_preview(article, images, workflow_id)

        if email_sent:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    {
                        "success": True,
                        "workflow_id": workflow_id,
                        "message": "Article generated and sent for approval",
                        "title": article["title"],
                    }
                ),
            }
        else:
            raise Exception("Failed to send email")

    except Exception as e:
        print(f"Error in workflow: {str(e)}")
        try:
            agent.workflow_table.put_item(
                Item={
                    "workflow_id": workflow_id,
                    "status": "error",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        except:
            pass

        return {
            "statusCode": 500,
            "body": json.dumps({"success": False, "error": str(e)}),
        }


def approval_handler(event, context):
    """Handle approval/decline from email link"""
    agent = BlogAgent()

    try:
        params = event.get("queryStringParameters", {})
        token = params.get("token")
        action = params.get("action")

        if not token or not action:
            return {"statusCode": 400, "body": "Missing token or action"}

        response = agent.workflow_table.scan(
            FilterExpression="approval_token = :token",
            ExpressionAttributeValues={":token": token},
        )

        items = response.get("Items", [])
        if not items:
            return {"statusCode": 404, "body": "Workflow not found or token expired"}

        workflow = items[0]
        workflow_id = workflow["workflow_id"]

        if action == 'approve':
            print(f"Approving workflow: {workflow_id}")

            # Reconstruct article and images (handle both single-agent and multi-agent formats)
            article_data = workflow.get('article_data')
            images_data = workflow.get('images_data')

            # Single-agent format: JSON strings
            if isinstance(article_data, str):
                article = json.loads(article_data)
                images = json.loads(images_data)
            # Multi-agent format: nested dicts
            elif isinstance(article_data, dict):
                article = article_data.get('article', {})
                images = article_data.get('images', [])

                # Multi-agent doesn't store original_topic in article, add it from workflow
                if 'original_topic' not in article and 'topic_category' in workflow:
                    article['original_topic'] = {
                        'category': workflow['topic_category'],
                        'title': workflow.get('topic_title', article.get('title', 'Unknown'))
                    }
            else:
                return {
                    "statusCode": 500,
                    "body": "Invalid article data format in workflow"
                }

            print(f"Article reconstructed, publishing to Sanity...")

            try:
                result = agent.publish_to_sanity(article, images)
                print(f"Publish result: {result}")
            except Exception as e:
                print(f"Publishing error: {str(e)}")
                import traceback
                traceback.print_exc()
                raise

            agent.workflow_table.update_item(
                Key={"workflow_id": workflow_id},
                UpdateExpression="SET #status = :status, published_url = :url, published_date = :date",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "published",
                    ":url": result["url"],
                    ":date": datetime.now(timezone.utc).isoformat(),
                },
            )

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": f"""
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #48bb78;">✅ Article Published!</h1>
                    <p>Your article has been successfully published.</p>
                    <p><a href="{result['url']}" style="color: #4299e1;">View Article</a></p>
                </body>
                </html>
                """,
            }

        elif action == "decline":
            print(f"Declining workflow: {workflow_id}")
            agent.workflow_table.update_item(
                Key={"workflow_id": workflow_id},
                UpdateExpression="SET #status = :status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": "declined"},
            )

            return {
                "statusCode": 200,
                "headers": {"Content-Type": "text/html"},
                "body": """
                <html>
                <body style="font-family: Arial; text-align: center; padding: 50px;">
                    <h1 style="color: #f56565;">❌ Article Declined</h1>
                    <p>The article has been declined and will not be published.</p>
                </body>
                </html>
                """,
            }
        else:
            return {"statusCode": 400, "body": "Invalid action"}

    except Exception as e:
        print(f"Error in approval handler: {str(e)}")
        return {"statusCode": 500, "body": f"Error: {str(e)}"}


def manual_trigger_handler(event, context):
    """Manual trigger for testing"""
    start_time = time.time()
    agent = BlogAgent()
    workflow_id = f"workflow-manual-{int(datetime.now().timestamp())}"

    try:
        # Check for in-progress workflows in last 10 minutes
        from boto3.dynamodb.conditions import Attr
        ten_min_ago = (datetime.now(timezone.utc).timestamp() - 600) * 1000  # milliseconds

        try:
            response = agent.workflow_table.scan(
                FilterExpression=(Attr('status').eq('in_progress') | Attr('status').eq('awaiting_approval')) &
                                Attr('created_at').gt(datetime.fromtimestamp(ten_min_ago/1000, timezone.utc).isoformat())
            )
            if response.get('Items'):
                print(f"Duplicate workflow detected. Blocking execution.")
                return {
                    "statusCode": 429,
                    "body": json.dumps({
                        "error": "Article generation already in progress. Please wait for email before triggering again.",
                        "existing_workflow_id": response['Items'][0].get('workflow_id')
                    })
                }
        except Exception as e:
            print(f"Warning: Could not check for duplicate workflows: {str(e)}")

        if "topic_title" in event:
            topic = next(
                (t for t in TOPIC_BANK if t["title"] == event["topic_title"]), None
            )
            if not topic:
                return {
                    "statusCode": 404,
                    "body": json.dumps({"error": "Topic not found"}),
                }
        else:
            topic = agent.select_next_topic()

        print(f"Manual trigger for topic: {topic['title']}")

        # CRITICAL: Create workflow entry immediately to prevent duplicate invocations
        agent.workflow_table.put_item(
            Item={
                "workflow_id": workflow_id,
                "status": "in_progress",
                "topic_title": topic['title'],
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        )
        print(f"Created workflow entry: {workflow_id}")

        article = agent.research_and_write(topic)
        images = agent.find_images(article)
        email_sent = agent.send_email_preview(article, images, workflow_id)

        # Publish metrics
        duration = time.time() - start_time
        agent._publish_metric("WorkflowDuration", duration, "Seconds", {"WorkflowType": "manual"})
        agent._publish_metric("WorkflowSuccess", 1, "Count", {"WorkflowType": "manual"})
        agent._publish_metric("ArticleWordCount", article.get("word_count", 0), "Count")

        # Estimate cost (rough approximation)
        input_tokens = 15000  # Approximate prompt size
        output_tokens = article.get("word_count", 0) * 1.3  # Rough estimate
        cost = (input_tokens / 1000 * 0.003) + (output_tokens / 1000 * 0.015)
        agent._publish_metric("WorkflowCost", cost, "None", {"WorkflowType": "manual"})

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "success": True,
                    "workflow_id": workflow_id,
                    "title": article["title"],
                    "word_count": article["word_count"],
                }
            ),
        }

    except Exception as e:
        # Publish error metric
        try:
            duration = time.time() - start_time
            agent._publish_metric("WorkflowDuration", duration, "Seconds", {"WorkflowType": "manual"})
            agent._publish_metric("WorkflowErrors", 1, "Count", {"WorkflowType": "manual"})
        except:
            pass
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
