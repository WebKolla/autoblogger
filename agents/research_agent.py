"""
Research Agent Module

Conducts comprehensive keyword research and content analysis using:
- Google Keyword Planner API for search volumes
- Web scraping for competitor insights
- Claude for research synthesis
"""

from typing import Dict, List, Optional
import requests
import json
from decimal import Decimal
from .base_agent import BaseAgent


class ResearchAgent(BaseAgent):
    """
    Research Agent

    Responsibilities:
    1. Google Keyword Research (search volumes, competition, related keywords)
    2. Content Research (competitor analysis, key facts)
    3. SEO Analysis (keyword difficulty, optimal length)
    4. Generate comprehensive research report
    """

    def __init__(self, workflow_id: str):
        """Initialize Research Agent"""
        super().__init__(workflow_id, agent_name="research")

        # Load Google Ads API credentials
        try:
            google_ads_secret = self.get_secrets("blog-google-ads-credentials")
            self.google_ads_client_id = google_ads_secret.get("client_id")
            self.google_ads_client_secret = google_ads_secret.get("client_secret")
            self.google_ads_refresh_token = google_ads_secret.get("refresh_token")
            self.google_ads_developer_token = google_ads_secret.get("developer_token")
            self.google_ads_customer_id = google_ads_secret.get("customer_id", "")
            self.log_event("Google Ads API credentials loaded")
        except Exception as e:
            self.log_event(f"Google Ads API credentials not found: {str(e)}", level="WARNING")
            self.google_ads_client_id = None

    def execute(self, input_data: Dict) -> Dict:
        """
        Main execution method

        Args:
            input_data: Must contain 'selected_topic' from Topic Discovery Agent

        Returns:
            Dict with comprehensive research report
        """
        try:
            self.update_agent_state(status="running")

            # Validate input
            self.validate_input(input_data, ["selected_topic"])
            selected_topic = input_data["selected_topic"]

            self.log_event(f"Starting research for: {selected_topic['title']}")

            # Step 1: Google Keyword Research
            keyword_research = self._conduct_keyword_research(selected_topic)

            # Step 2: Generate research synthesis with Claude
            research_synthesis = self._synthesize_research(selected_topic, keyword_research)

            # Step 3: Build comprehensive report
            research_report = {
                "topic_title": selected_topic["title"],
                "topic_category": selected_topic["category"],
                "keyword_research": keyword_research,
                "research_synthesis": research_synthesis,
                "content_recommendations": self._generate_content_recommendations(
                    selected_topic, keyword_research
                )
            }

            # Update agent state
            self.update_agent_state(status="completed", output=research_report)

            return {
                "status": "success",
                "research_report": research_report
            }

        except Exception as e:
            self.handle_error(e, context="Research Agent execution")
            raise

    def _conduct_keyword_research(self, topic: Dict) -> Dict:
        """
        Conduct keyword research using Google Keyword Planner API

        Args:
            topic: Selected topic dict

        Returns:
            Dict with keyword data
        """
        try:
            keywords = topic.get("keywords", [])

            if not self.google_ads_client_id or not self.google_ads_refresh_token:
                self.log_event("Google Ads API not configured, using static keywords", level="WARNING")
                return self._get_static_keyword_data(keywords)

            # Get OAuth2 access token
            access_token = self._get_google_oauth_token()

            if not access_token:
                return self._get_static_keyword_data(keywords)

            # Fetch keyword ideas (simplified - actual Google Ads API is more complex)
            keyword_data = self._fetch_keyword_ideas(keywords, access_token)

            self.log_event(f"Keyword research complete: {len(keyword_data.get('primary_keywords', []))} primary keywords")

            return keyword_data

        except Exception as e:
            self.log_event(f"Error in keyword research: {str(e)}", level="ERROR")
            return self._get_static_keyword_data(topic.get("keywords", []))

    def _get_google_oauth_token(self) -> Optional[str]:
        """Get OAuth2 access token from Google"""
        try:
            response = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.google_ads_client_id,
                    "client_secret": self.google_ads_client_secret,
                    "refresh_token": self.google_ads_refresh_token,
                    "grant_type": "refresh_token"
                },
                timeout=10
            )

            if response.status_code == 200:
                access_token = response.json().get("access_token")
                self.log_event("OAuth2 token obtained successfully")
                return access_token
            else:
                self.log_event(f"OAuth2 token error: {response.text}", level="ERROR")
                return None

        except Exception as e:
            self.log_event(f"Error getting OAuth token: {str(e)}", level="ERROR")
            return None

    def _fetch_keyword_ideas(self, keywords: List[str], access_token: str) -> Dict:
        """
        Fetch keyword ideas from Google Ads API

        Note: This is a simplified implementation. Full implementation requires
        the google-ads Python library and proper API setup.
        """
        try:
            # For now, return enhanced static data with simulated API response
            # TODO: Implement actual Google Ads API call when google-ads library is added

            self.log_event("Using simulated Google Ads API response (TODO: implement actual API)")

            primary_keywords = []
            for i, keyword in enumerate(keywords[:3]):
                primary_keywords.append({
                    "keyword": keyword,
                    "volume": 500 + (i * 200),  # Simulated
                    "difficulty": "medium",
                    "cpc": round(0.8 + (i * 0.3), 2),
                    "trend": "stable"
                })

            secondary_keywords = keywords[3:6] if len(keywords) > 3 else []
            long_tail_keywords = [
                f"{keywords[0]} guide",
                f"{keywords[0]} tips",
                f"best {keywords[0]}"
            ]

            return {
                "primary_keywords": primary_keywords,
                "secondary_keywords": secondary_keywords,
                "long_tail_keywords": long_tail_keywords,
                "keyword_density_target": 1.5
            }

        except Exception as e:
            self.log_event(f"Error fetching keyword ideas: {str(e)}", level="ERROR")
            return self._get_static_keyword_data(keywords)

    def _get_static_keyword_data(self, keywords: List[str]) -> Dict:
        """Fallback: Return static keyword data"""
        primary_keywords = []
        for i, keyword in enumerate(keywords[:3]):
            primary_keywords.append({
                "keyword": keyword,
                "volume": 400,
                "difficulty": "medium",
                "cpc": 1.0,
                "trend": "stable"
            })

        return {
            "primary_keywords": primary_keywords,
            "secondary_keywords": keywords[3:6] if len(keywords) > 3 else [],
            "long_tail_keywords": [
                f"{keywords[0]} guide" if keywords else "cycling sri lanka guide",
                f"{keywords[0]} tips" if keywords else "cycling sri lanka tips"
            ],
            "keyword_density_target": 1.5
        }

    def _synthesize_research(self, topic: Dict, keyword_research: Dict) -> Dict:
        """
        Use Claude to synthesize research findings

        Args:
            topic: Selected topic
            keyword_research: Keyword research data

        Returns:
            Dict with research synthesis
        """
        try:
            # Build prompt for Claude
            prompt = self._build_research_prompt(topic, keyword_research)

            # Invoke Claude
            response = self.invoke_claude(
                prompt=prompt,
                max_tokens=4096,
                temperature=0.5,  # Lower temperature for factual research
                system="You are an expert travel and SEO researcher specializing in cycling tourism in Sri Lanka."
            )

            # Parse Claude's response
            try:
                synthesis = json.loads(response)
            except json.JSONDecodeError:
                # If Claude doesn't return valid JSON, create structured data
                self.log_event("Claude response not valid JSON, using fallback structure", level="WARNING")
                synthesis = {
                    "key_facts": [
                        "Sri Lanka is a premier cycling destination",
                        "Best season for cycling: November to April",
                        "UNESCO World Heritage Sites accessible by bike"
                    ],
                    "practical_info": {
                        "best_season": "November to April",
                        "avg_temperature": "28-32°C",
                        "visa_requirement": "ETA required",
                        "cycling_difficulty": "Moderate"
                    },
                    "content_angle": "Unique cycling experience combining culture and nature"
                }

            self.log_event("Research synthesis complete")
            return synthesis

        except Exception as e:
            self.log_event(f"Error in research synthesis: {str(e)}", level="ERROR")
            return {
                "key_facts": ["Research synthesis failed - using fallback"],
                "practical_info": {},
                "content_angle": topic.get("title", "")
            }

    def _build_research_prompt(self, topic: Dict, keyword_research: Dict) -> str:
        """Build Claude prompt for research synthesis"""

        primary_keywords = [kw["keyword"] for kw in keyword_research.get("primary_keywords", [])]

        prompt = f"""You are conducting research for a blog article about: {topic['title']}

TOPIC DETAILS:
- Category: {topic['category']}
- Target Keywords: {', '.join(primary_keywords)}

YOUR TASK:
Research and provide comprehensive information for this article. Focus on:

1. KEY FACTS (5-8 facts):
   - Historical context
   - Geographic details
   - Statistics and data
   - Notable features or attractions
   - Best times to visit

2. PRACTICAL INFORMATION:
   - Best season for cycling
   - Average temperature
   - Visa requirements
   - Difficulty level
   - Recommended duration
   - Safety considerations

3. UNIQUE ANGLE:
   - What makes this topic/route unique?
   - How is it different from other cycling experiences?
   - What competitors haven't covered?

4. MUST-INCLUDE ELEMENTS:
   - Across Ceylon tour operator mentions (natural placement)
   - Local cultural insights
   - Practical cycling logistics

Return your response as a JSON object with this structure:
{{
  "key_facts": [
    "Fact 1",
    "Fact 2",
    ...
  ],
  "statistics": [
    "Statistic 1",
    "Statistic 2"
  ],
  "practical_info": {{
    "best_season": "...",
    "avg_temperature": "...",
    "visa_requirement": "...",
    "cycling_difficulty": "...",
    "recommended_duration": "...",
    "safety_tips": ["tip1", "tip2"]
  }},
  "unique_angle": "Description of what makes this unique...",
  "content_angle": "The primary storytelling approach for this article",
  "must_include": [
    "Element 1",
    "Element 2"
  ]
}}

Provide accurate, engaging information suitable for an adventure cycling blog."""

        return prompt

    def _generate_content_recommendations(self, topic: Dict, keyword_research: Dict) -> Dict:
        """
        Generate content recommendations based on research

        Args:
            topic: Selected topic
            keyword_research: Keyword research results

        Returns:
            Dict with content recommendations
        """
        # Calculate target word count based on keyword volume
        avg_volume = sum(kw.get("volume", 400) for kw in keyword_research.get("primary_keywords", [])) / max(len(keyword_research.get("primary_keywords", [])), 1)

        if avg_volume > 800:
            target_length = "3000-3500 words"
        elif avg_volume > 400:
            target_length = "2500-3000 words"
        else:
            target_length = "2000-2500 words"

        return {
            "target_length": target_length,
            "tone": "Educational + Inspirational",
            "structure": "Introduction → 8-10 key sections → Practical tips → CTA",
            "must_include": [
                "UNESCO site descriptions" if "cultural" in topic.get("category", "").lower() else "Route details",
                "Best season & weather info",
                "Visa requirements",
                "Safety tips",
                "Recommended tour operators (Across Ceylon)",
                "Accommodation suggestions",
                "Local cultural insights"
            ],
            "internal_links": [
                {
                    "anchor": f"{topic['category']} tour package",
                    "url": "/packages/custom-tour",
                    "context": f"Experience our guided {topic['category']} tours"
                }
            ],
            "estimated_time_to_write": "45-60 minutes"
        }
