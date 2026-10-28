import hashlib
import json
from datetime import datetime, timezone
import uuid
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

# In a real app, this key would be fetched dynamically from Vault KV.
# For scaffolding, we mock a static Ed25519 signer logic.
class MockEd25519Signer:
    def sign(self, data: bytes) -> bytes:
        # Mock signature for Phase 1 dev
        return b"mock_ed25519_signature_of_" + hashlib.sha256(data).digest()

signer = MockEd25519Signer()

class AuditService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def _get_last_hash(self) -> Optional[str]:
        """Fetch the entry_hash of the most recent audit log to continue the chain."""
        query = text("SELECT entry_hash FROM audit_logs ORDER BY seq DESC LIMIT 1")
        result = await self.session.execute(query)
        row = result.fetchone()
        return row[0] if row else None

    async def log_event(
        self,
        actor_id: uuid.UUID,
        actor_role: str,
        actor_ip: str,
        action: str,
        resource_type: str,
        resource_id: Optional[uuid.UUID] = None,
        case_id: Optional[uuid.UUID] = None,
        outcome: str = "SUCCESS",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Append an immutable, hash-chained log entry to the audit_logs table."""
        timestamp = datetime.now(timezone.utc)
        
        # Privacy-preserving IP hash
        ip_salt = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        actor_ip_hash = hashlib.sha256(f"{actor_ip}{ip_salt}".encode()).hexdigest()

        # Get previous hash to link the blockchain
        prev_hash = await self.get_last_hash()
        if not prev_hash:
            prev_hash = "0" * 64  # Genesis entry

        # Construct the entry body for hashing
        entry_body = {
            "prev_hash": prev_hash,
            "timestamp": timestamp.isoformat(),
            "actor_id": str(actor_id),
            "actor_role": actor_role,
            "action": action,
            "resource_type": resource_type,
            "resource_id": str(resource_id) if resource_id else None,
            "outcome": outcome,
        }
        
        # Calculate current entry hash
        entry_body_str = json.dumps(entry_body, sort_keys=True)
        entry_hash = hashlib.sha256(entry_body_str.encode()).hexdigest()
        
        # Sign the hash with the system Ed25519 key
        entry_sig = signer.sign(entry_hash.encode())

        insert_query = text("""
            INSERT INTO audit_logs (
                prev_hash, timestamp, actor_id, actor_ip_hash, actor_role, 
                action, resource_type, resource_id, case_id, outcome, 
                metadata, entry_hash, entry_sig
            ) VALUES (
                :prev_hash, :timestamp, :actor_id, :actor_ip_hash, :actor_role,
                :action, :resource_type, :resource_id, :case_id, :outcome,
                :metadata, :entry_hash, :entry_sig
            )
        """)

        await self.session.execute(insert_query, {
            "prev_hash": prev_hash,
            "timestamp": timestamp,
            "actor_id": actor_id,
            "actor_ip_hash": actor_ip_hash,
            "actor_role": actor_role,
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "case_id": case_id,
            "outcome": outcome,
            "metadata": json.dumps(metadata) if metadata else None,
            "entry_hash": entry_hash,
            "entry_sig": entry_sig
        })
        
        await self.session.commit()
        return entry_hash

    async def verify_chain(self) -> bool:
        """Verify the integrity of the entire audit hash chain."""
        # This will iterate through seq numbers ensuring prev_hash matches.
        # Implemented fully in Phase 4.
        pass
