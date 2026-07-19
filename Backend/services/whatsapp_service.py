# Backend/services/whatsapp_service.py
import os
from config import Config
import logging

logger = logging.getLogger(__name__)

class WhatsAppService:
    
    @staticmethod
    def enviar(telefono, mensaje):
        try:
            from twilio.rest import Client
            
            if not Config.TWILIO_ACCOUNT_SID or not Config.TWILIO_AUTH_TOKEN or not Config.TWILIO_WHATSAPP_FROM:
                return {"success": False, "error": "Credenciales no configuradas"}
            
            client = Client(Config.TWILIO_ACCOUNT_SID, Config.TWILIO_AUTH_TOKEN)
            
            if not telefono.startswith('+'):
                telefono = '+' + telefono
            
            message = client.messages.create(
                body=mensaje,
                from_=Config.TWILIO_WHATSAPP_FROM,
                to=f'whatsapp:{telefono}'
            )
            
            return {"success": True, "sid": message.sid}
            
        except Exception as e:
            logger.error(f"Error enviando WhatsApp: {e}")
            return {"success": False, "error": str(e)}
