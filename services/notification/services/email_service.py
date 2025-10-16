
import smtplib
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import structlog

from core.config import settings

logger = structlog.get_logger(__name__)


class EmailService:
    """Email sending service"""
    
    def __init__(self):
        self.emails_sent = 0
        self.emails_failed = 0
        self.rate_limit_window = timedelta(minutes=1)
        self.recent_sends = []
    
    async def test_connection(self):
        """Test SMTP connection"""
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.warning("SMTP credentials not configured")
            return
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._test_smtp_connection
            )
            logger.info("SMTP connection test successful")
        
        except Exception as e:
            logger.error("SMTP connection test failed", error=str(e))
            raise
    
    def _test_smtp_connection(self):
        """Test SMTP connection (synchronous)"""
        try:
            server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.quit()
        except Exception as e:
            raise Exception(f"SMTP connection failed: {str(e)}")
    
    async def send_review_completion_email(self, review_data: Dict) -> bool:
        """Send review completion notification email"""
        try:
            # Check rate limiting
            if not self._check_rate_limit():
                logger.warning("Email rate limit exceeded, skipping send")
                return False
            
            # Determine recipient
            recipient = self._get_recipient_email(review_data)
            if not recipient:
                logger.warning("No recipient email available")
                return False
            
            # Build email content
            subject, body = self._build_review_email(review_data)
            
            # Send email
            success = await self._send_email(recipient, subject, body)
            
            if success:
                self.emails_sent += 1
                logger.info("Review completion email sent", 
                          recipient=recipient,
                          review_id=review_data.get("review_id"))
            else:
                self.emails_failed += 1
            
            return success
            
        except Exception as e:
            logger.error("Failed to send review completion email", error=str(e))
            self.emails_failed += 1
            return False
    
    def _get_recipient_email(self, review_data: Dict) -> Optional[str]:
        """Get recipient email from review data"""
        # Try to get email from review data
        recipient = review_data.get("author_email")
        
        # Fall back to configured default
        if not recipient:
            recipient = settings.SMTP_TO_EMAIL
        
        return recipient
    
    def _build_review_email(self, review_data: Dict) -> tuple[str, str]:
        """Build email subject and body"""
        upload_id = review_data.get("upload_id", "unknown")
        review_id = review_data.get("review_id", "unknown")
        overall_score = review_data.get("overall_score", 0)
        suggestions_count = review_data.get("suggestions_count", 0)
        summary = review_data.get("summary", "No summary available")
        
        # Subject
        subject = f"AI Code Review Complete - Score: {overall_score}/100 (ID: {upload_id[:8]})"
        
        # Body
        body = f"""
Hi there,

Your AI code review has been completed! Here are the results:

📊 Review Summary:
- Upload ID: {upload_id}
- Overall Quality Score: {overall_score}/100
- Issues Found: {suggestions_count}
- Summary: {summary}

The detailed review results are available in your dashboard.

Key Findings:
- Quality Score: {self._get_score_description(overall_score)}
- Total Suggestions: {suggestions_count}

What's Next:
1. Review the detailed suggestions in your dashboard
2. Address high-priority issues first
3. Consider the recommendations for code improvements

Thank you for using AI Code Review!

Best regards,
AI Code Review Team

---
This is an automated message. Please do not reply to this email.
Upload ID: {upload_id}
Review ID: {review_id}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}
"""
        
        return subject, body
    
    def _get_score_description(self, score: int) -> str:
        """Get description for quality score"""
        if score >= 90:
            return "Excellent - Very high quality code"
        elif score >= 80:
            return "Good - Quality code with minor improvements needed"
        elif score >= 70:
            return "Fair - Some issues to address"
        elif score >= 60:
            return "Poor - Several improvements needed"
        else:
            return "Needs Work - Significant improvements required"
    
    async def _send_email(self, recipient: str, subject: str, body: str) -> bool:
        """Send email (async wrapper)"""
        if not settings.SMTP_USERNAME or not settings.SMTP_PASSWORD:
            logger.warning("SMTP not configured, skipping email send")
            return False
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, self._send_email_sync, recipient, subject, body
            )
            return True
            
        except Exception as e:
            logger.error("Email send failed", error=str(e), recipient=recipient)
            return False
    
    def _send_email_sync(self, recipient: str, subject: str, body: str):
        """Send email synchronously"""
        msg = MIMEMultipart()
        msg['From'] = settings.SMTP_FROM_EMAIL
        msg['To'] = recipient
        msg['Subject'] = subject
        
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
    
    def _check_rate_limit(self) -> bool:
        """Check if within rate limit"""
        now = datetime.utcnow()
        cutoff = now - self.rate_limit_window
        
        # Remove old entries
        self.recent_sends = [send_time for send_time in self.recent_sends if send_time > cutoff]
        
        # Check limit
        if len(self.recent_sends) >= settings.EMAIL_RATE_LIMIT:
            return False
        
        # Add current send
        self.recent_sends.append(now)
        return True
    
    async def close(self):
        """Close email service"""
        logger.info("Email service closed")

