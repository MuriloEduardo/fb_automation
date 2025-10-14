from typing import Dict, List
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class LeadsCollector:
    
    def __init__(self, api_client):
        self.api_client = api_client
    
    def get_leadgen_forms(self, page_id: str) -> Dict:
        endpoint = f"{page_id}/leadgen_forms"
        params = {
            'fields': 'id,name,status,leads_count,created_time,locale,privacy_policy_url,follow_up_action_url',
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            forms = response.get('data', [])
            
            return {
                'status': 'success',
                'page_id': page_id,
                'total_forms': len(forms),
                'forms': forms,
                'collected_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            error_str = str(e)
            
            if '403' in error_str or 'Forbidden' in error_str:
                logger.warning(f"Página {page_id} não tem permissão para acessar leads (403 Forbidden)")
                return {
                    'status': 'no_permission',
                    'page_id': page_id,
                    'error': 'Permissões insuficientes para acessar leads. Necessário: pages_manage_ads, pages_read_engagement, leads_retrieval',
                    'forms': [],
                }
            
            logger.error(f"Erro ao buscar formulários de leads da página {page_id}: {e}")
            return {
                'status': 'error',
                'page_id': page_id,
                'error': str(e),
                'forms': [],
            }
    
    def get_form_leads(self, form_id: str) -> Dict:
        endpoint = f"{form_id}/leads"
        params = {
            'fields': 'id,created_time,field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,form_id,is_organic',
        }
        
        try:
            response = self.api_client._make_request('GET', endpoint, params)
            
            leads = response.get('data', [])
            
            parsed_leads = []
            for lead in leads:
                parsed_lead = {
                    'lead_id': lead.get('id'),
                    'created_time': lead.get('created_time'),
                    'is_organic': lead.get('is_organic', True),
                    'ad_id': lead.get('ad_id'),
                    'ad_name': lead.get('ad_name'),
                    'adset_id': lead.get('adset_id'),
                    'adset_name': lead.get('adset_name'),
                    'campaign_id': lead.get('campaign_id'),
                    'campaign_name': lead.get('campaign_name'),
                    'form_id': lead.get('form_id'),
                    'fields': {},
                }
                
                for field in lead.get('field_data', []):
                    field_name = field.get('name')
                    field_values = field.get('values', [])
                    parsed_lead['fields'][field_name] = field_values[0] if field_values else None
                
                parsed_leads.append(parsed_lead)
            
            return {
                'status': 'success',
                'form_id': form_id,
                'total_leads': len(parsed_leads),
                'leads': parsed_leads,
                'collected_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            error_str = str(e)
            
            if '403' in error_str or 'Forbidden' in error_str:
                logger.warning(f"Sem permissão para acessar leads do formulário {form_id} (403 Forbidden)")
                return {
                    'status': 'no_permission',
                    'form_id': form_id,
                    'error': 'Permissões insuficientes para acessar leads',
                    'leads': [],
                }
            
            logger.error(f"Erro ao buscar leads do formulário {form_id}: {e}")
            return {
                'status': 'error',
                'form_id': form_id,
                'error': str(e),
                'leads': [],
            }
    
    def get_all_leads(self, page_id: str) -> Dict:
        forms_result = self.get_leadgen_forms(page_id)
        
        if forms_result['status'] not in ['success', 'no_permission']:
            return forms_result
        
        if forms_result['status'] == 'no_permission':
            return {
                'status': 'no_permission',
                'page_id': page_id,
                'error': forms_result['error'],
                'total_leads': 0,
                'leads': [],
            }
        
        all_leads = []
        forms_with_leads = []
        
        for form in forms_result['forms']:
            form_id = form['id']
            form_name = form['name']
            
            leads_result = self.get_form_leads(form_id)
            
            if leads_result['status'] == 'success':
                if leads_result['total_leads'] > 0:
                    forms_with_leads.append({
                        'form_id': form_id,
                        'form_name': form_name,
                        'leads_count': leads_result['total_leads'],
                    })
                    
                    for lead in leads_result['leads']:
                        lead['form_name'] = form_name
                        all_leads.append(lead)
        
        return {
            'status': 'success',
            'page_id': page_id,
            'total_forms': len(forms_result['forms']),
            'forms_with_leads': len(forms_with_leads),
            'total_leads': len(all_leads),
            'forms': forms_with_leads,
            'leads': all_leads,
            'collected_at': timezone.now().isoformat(),
        }
    
    def get_lead_details(self, lead_id: str) -> Dict:
        endpoint = f"{lead_id}/"
        params = {
            'fields': 'id,created_time,field_data,ad_id,ad_name,adset_id,adset_name,campaign_id,campaign_name,form_id,is_organic',
        }
        
        try:
            lead = self.api_client._make_request('GET', endpoint, params)
            
            parsed_lead = {
                'lead_id': lead.get('id'),
                'created_time': lead.get('created_time'),
                'is_organic': lead.get('is_organic', True),
                'ad_id': lead.get('ad_id'),
                'ad_name': lead.get('ad_name'),
                'adset_id': lead.get('adset_id'),
                'adset_name': lead.get('adset_name'),
                'campaign_id': lead.get('campaign_id'),
                'campaign_name': lead.get('campaign_name'),
                'form_id': lead.get('form_id'),
                'fields': {},
            }
            
            for field in lead.get('field_data', []):
                field_name = field.get('name')
                field_values = field.get('values', [])
                parsed_lead['fields'][field_name] = field_values[0] if field_values else None
            
            return {
                'status': 'success',
                'lead': parsed_lead,
                'collected_at': timezone.now().isoformat(),
            }
            
        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do lead {lead_id}: {e}")
            return {
                'status': 'error',
                'lead_id': lead_id,
                'error': str(e),
            }
