from typing import Dict, List, Optional
from datetime import datetime, timedelta
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class InsightsCollector:
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    def get_page_insights(
        self, 
        page_id: str, 
        metrics: List[str],
        period: str = 'day',
        days_back: int = 30
    ) -> Dict:
        
        since_date = (timezone.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')
        until_date = timezone.now().strftime('%Y-%m-%d')
        
        endpoint = f"{page_id}/insights"
        params = {
            'metric': ','.join(metrics),
            'period': period,
            'since': since_date,
            'until': until_date,
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            insights_data = {}
            for metric_data in response.get('data', []):
                metric_name = metric_data.get('name')
                values = metric_data.get('values', [])
                
                insights_data[metric_name] = {
                    'title': metric_data.get('title'),
                    'description': metric_data.get('description'),
                    'period': metric_data.get('period'),
                    'values': values,
                    'latest_value': values[-1].get('value') if values else None,
                }
            
            return {
                'status': 'success',
                'page_id': page_id,
                'insights': insights_data,
                'period': period,
                'date_range': {
                    'since': since_date,
                    'until': until_date,
                },
                'collected_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Erro ao coletar insights da página {page_id}: {e}")
            return {
                'status': 'error',
                'page_id': page_id,
                'error': str(e),
                'insights': {},
            }
    
    def get_demographics(self, page_id: str, days_back: int = 30) -> Dict:
        demographic_metrics = [
            'page_fans_gender_age',
            'page_fans_country',
            'page_fans_city',
            'page_impressions_by_age_gender_unique',
        ]
        
        result = self.get_page_insights(
            page_id, 
            demographic_metrics, 
            period='day',
            days_back=days_back
        )
        
        if result['status'] == 'success':
            demographics = {
                'gender_age': self._parse_gender_age(
                    result['insights'].get('page_fans_gender_age', {})
                ),
                'countries': self._parse_location(
                    result['insights'].get('page_fans_country', {})
                ),
                'cities': self._parse_location(
                    result['insights'].get('page_fans_city', {})
                ),
                'impressions_demographics': self._parse_gender_age(
                    result['insights'].get('page_impressions_by_age_gender_unique', {})
                ),
            }
            
            result['demographics'] = demographics
        
        return result
    
    def get_engagement_insights(self, page_id: str, days_back: int = 30) -> Dict:
        engagement_metrics = [
            'page_engaged_users',
            'page_post_engagements',
            'page_actions_post_reactions_total',
            'page_positive_feedback',
            'page_negative_feedback',
        ]
        
        return self.get_page_insights(
            page_id,
            engagement_metrics,
            period='day',
            days_back=days_back
        )
    
    def get_reach_insights(self, page_id: str, days_back: int = 30) -> Dict:
        reach_metrics = [
            'page_impressions',
            'page_impressions_unique',
            'page_impressions_paid',
            'page_impressions_organic',
            'page_impressions_viral',
            'page_posts_impressions',
            'page_posts_impressions_paid',
            'page_posts_impressions_organic',
            'page_posts_impressions_viral',
        ]
        
        return self.get_page_insights(
            page_id,
            reach_metrics,
            period='day',
            days_back=days_back
        )
    
    def get_page_views_insights(self, page_id: str, days_back: int = 30) -> Dict:
        views_metrics = [
            'page_views_total',
            'page_views_logged_in_unique',
            'page_video_views',
            'page_video_views_paid',
            'page_video_views_organic',
        ]
        
        return self.get_page_insights(
            page_id,
            views_metrics,
            period='day',
            days_back=days_back
        )
    
    def get_fans_insights(self, page_id: str, days_back: int = 30) -> Dict:
        fans_metrics = [
            'page_fans',
            'page_fan_adds',
            'page_fan_removes',
            'page_fan_adds_unique',
            'page_fans_online',
            'page_fans_by_like_source',
        ]
        
        return self.get_page_insights(
            page_id,
            fans_metrics,
            period='day',
            days_back=days_back
        )
    
    def get_complete_insights(self, page_id: str, days_back: int = 30) -> Dict:
        
        complete_data = {
            'page_id': page_id,
            'date_range': {
                'since': (timezone.now() - timedelta(days=days_back)).strftime('%Y-%m-%d'),
                'until': timezone.now().strftime('%Y-%m-%d'),
            },
            'collected_at': timezone.now().isoformat(),
        }
        
        complete_data['demographics'] = self.get_demographics(page_id, days_back)
        complete_data['engagement'] = self.get_engagement_insights(page_id, days_back)
        complete_data['reach'] = self.get_reach_insights(page_id, days_back)
        complete_data['page_views'] = self.get_page_views_insights(page_id, days_back)
        complete_data['fans'] = self.get_fans_insights(page_id, days_back)
        
        complete_data['summary'] = self._create_summary(complete_data)
        
        return complete_data
    
    def _parse_gender_age(self, metric_data: Dict) -> Dict:
        latest_value = metric_data.get('latest_value', {})
        
        if not latest_value:
            return {}
        
        parsed = {
            'male': {},
            'female': {},
            'unknown': {},
        }
        
        for key, value in latest_value.items():
            if key.startswith('M.'):
                age_range = key.replace('M.', '')
                parsed['male'][age_range] = value
            elif key.startswith('F.'):
                age_range = key.replace('F.', '')
                parsed['female'][age_range] = value
            elif key.startswith('U.'):
                age_range = key.replace('U.', '')
                parsed['unknown'][age_range] = value
        
        return parsed
    
    def _parse_location(self, metric_data: Dict) -> Dict:
        latest_value = metric_data.get('latest_value', {})
        
        if not latest_value:
            return {}
        
        sorted_locations = sorted(
            latest_value.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        return dict(sorted_locations[:10])
    
    def _create_summary(self, complete_data: Dict) -> Dict:
        summary = {}
        
        demographics = complete_data.get('demographics', {}).get('demographics', {})
        if demographics:
            gender_age = demographics.get('gender_age', {})
            total_male = sum(gender_age.get('male', {}).values())
            total_female = sum(gender_age.get('female', {}).values())
            
            summary['gender_distribution'] = {
                'male': total_male,
                'female': total_female,
                'male_percentage': round(total_male / (total_male + total_female) * 100, 1) if (total_male + total_female) > 0 else 0,
            }
            
            summary['top_countries'] = list(demographics.get('countries', {}).keys())[:5]
            summary['top_cities'] = list(demographics.get('cities', {}).keys())[:5]
        
        engagement_data = complete_data.get('engagement', {}).get('insights', {})
        if engagement_data:
            engaged_users = engagement_data.get('page_engaged_users', {}).get('latest_value')
            summary['engaged_users'] = engaged_users if engaged_users else 0
        
        reach_data = complete_data.get('reach', {}).get('insights', {})
        if reach_data:
            summary['total_impressions'] = reach_data.get('page_impressions', {}).get('latest_value', 0)
            summary['organic_impressions'] = reach_data.get('page_impressions_organic', {}).get('latest_value', 0)
            summary['paid_impressions'] = reach_data.get('page_impressions_paid', {}).get('latest_value', 0)
            summary['viral_impressions'] = reach_data.get('page_impressions_viral', {}).get('latest_value', 0)
        
        fans_data = complete_data.get('fans', {}).get('insights', {})
        if fans_data:
            summary['total_fans'] = fans_data.get('page_fans', {}).get('latest_value', 0)
            summary['new_fans'] = fans_data.get('page_fan_adds', {}).get('latest_value', 0)
            summary['lost_fans'] = fans_data.get('page_fan_removes', {}).get('latest_value', 0)
        
        return summary
    
    def get_post_insights(self, post_id: str) -> Dict:
        endpoint = f"{post_id}/insights"
        params = {
            'metric': ','.join([
                'post_impressions',
                'post_impressions_unique',
                'post_impressions_paid',
                'post_impressions_organic',
                'post_impressions_viral',
                'post_engaged_users',
                'post_clicks',
                'post_reactions_by_type_total',
            ])
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            insights_data = {}
            for metric_data in response.get('data', []):
                metric_name = metric_data.get('name')
                values = metric_data.get('values', [])
                
                insights_data[metric_name] = {
                    'title': metric_data.get('title'),
                    'value': values[0].get('value') if values else None,
                }
            
            return {
                'status': 'success',
                'post_id': post_id,
                'insights': insights_data,
                'collected_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Erro ao coletar insights do post {post_id}: {e}")
            return {
                'status': 'error',
                'post_id': post_id,
                'error': str(e),
                'insights': {},
            }
