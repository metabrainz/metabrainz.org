from sqlalchemy import Column, Integer, Identity, Text, DateTime, func

from metabrainz.model import db


class DomainBlacklist(db.Model):
    """Model for storing blacklisted email domains to block registration."""
    __tablename__ = 'domain_blacklist'

    id = Column(Integer, Identity(), primary_key=True)
    domain = Column(Text, unique=True, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), nullable=False, default=func.now())

    @classmethod
    def is_domain_blacklisted(cls, domain):
        """Check if a domain is blacklisted.

        Args:
            domain: The email domain to check (e.g., 'example.com')

        Returns:
            bool: True if the domain is blacklisted, False otherwise
        """
        domain = domain.lower().strip()
        return cls.query.filter_by(domain=domain).first() is not None

    @classmethod
    def is_email_blacklisted(cls, email):
        """Check if an email's domain is blacklisted.

        Args:
            email: The full email address to check

        Returns:
            bool: True if the email's domain is blacklisted, False otherwise
        """
        if not email or '@' not in email:
            return False
        domain = email.split('@')[1].lower().strip()
        return cls.is_domain_blacklisted(domain)

    @classmethod
    def add(cls, domain, reason=None):
        """Add a domain to the blacklist.

        Args:
            domain: The domain to blacklist
            reason: Optional reason for blacklisting

        Returns:
            DomainBlacklist: The created entry
        """
        domain = domain.lower().strip()
        entry = cls(domain=domain, reason=reason)
        db.session.add(entry)
        return entry

    def __repr__(self):
        return f'<DomainBlacklist {self.domain}>'
