"""Database models and caching layer for analysis results.

Uses Neon PostgreSQL to cache analysis responses for 24 hours.
"""
from __future__ import annotations

import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from sqlalchemy import create_engine, Column, String, Text, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from contextlib import contextmanager


from dotenv import load_dotenv
load_dotenv()

Base = declarative_base()


class AnalysisCache(Base):
    """Cache table for storing analysis results."""
    __tablename__ = 'analysis_cache'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    pair_key = Column(String(100), unique=True, nullable=False, index=True)
    symbol_a = Column(String(50), nullable=False)
    symbol_b = Column(String(50), nullable=False)
    metrics_json = Column(Text, nullable=False)
    analysis_json = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "symbolA": self.symbol_a,
            "symbolB": self.symbol_b,
            "metrics": json.loads(self.metrics_json),
            "analysis": json.loads(self.analysis_json),
            "cached": True,
            "cached_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat(),
        }


class CacheManager:
    """Manages database connections and caching operations."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize cache manager with database URL."""
        self.database_url = database_url or os.getenv("DATABASE_URL")
        
        if not self.database_url:
            raise ValueError("DATABASE_URL not configured")
        
        # Create engine
        self.engine = create_engine(
            self.database_url,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        
        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(self.engine)
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def _make_pair_key(self, symbol_a: str, symbol_b: str) -> str:
        """Generate cache key for trading pair."""
        return f"{symbol_a.upper()}:{symbol_b.upper()}"
    
    def get_cached_analysis(
        self,
        symbol_a: str,
        symbol_b: str
    ) -> Optional[Dict[str, Any]]:
        """Get cached analysis if available and not expired."""
        pair_key = self._make_pair_key(symbol_a, symbol_b)
        
        with self.get_session() as session:
            # Query for non-expired cache entry
            cache_entry = session.query(AnalysisCache).filter(
                AnalysisCache.pair_key == pair_key,
                AnalysisCache.expires_at > datetime.utcnow()
            ).first()
            
            if cache_entry:
                return cache_entry.to_dict()
            
            return None
    
    def cache_analysis(
        self,
        symbol_a: str,
        symbol_b: str,
        metrics: Dict[str, Any],
        analysis: Dict[str, Any],
        ttl_hours: int = 24
    ) -> None:
        """Cache analysis result with TTL."""
        pair_key = self._make_pair_key(symbol_a, symbol_b)
        now = datetime.utcnow()
        expires_at = now + timedelta(hours=ttl_hours)
        
        with self.get_session() as session:
            # Check if entry exists
            existing = session.query(AnalysisCache).filter(
                AnalysisCache.pair_key == pair_key
            ).first()
            
            if existing:
                # Update existing entry
                existing.metrics_json = json.dumps(metrics)
                existing.analysis_json = json.dumps(analysis)
                existing.created_at = now
                existing.expires_at = expires_at
            else:
                # Create new entry
                cache_entry = AnalysisCache(
                    pair_key=pair_key,
                    symbol_a=symbol_a,
                    symbol_b=symbol_b,
                    metrics_json=json.dumps(metrics),
                    analysis_json=json.dumps(analysis),
                    created_at=now,
                    expires_at=expires_at,
                )
                session.add(cache_entry)
    
    def cleanup_expired(self) -> int:
        """Remove expired cache entries. Returns number of deleted entries."""
        with self.get_session() as session:
            deleted = session.query(AnalysisCache).filter(
                AnalysisCache.expires_at <= datetime.utcnow()
            ).delete()
            return deleted
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self.get_session() as session:
            total = session.query(AnalysisCache).count()
            valid = session.query(AnalysisCache).filter(
                AnalysisCache.expires_at > datetime.utcnow()
            ).count()
            expired = total - valid
            
            return {
                "total_entries": total,
                "valid_entries": valid,
                "expired_entries": expired,
            }


# Singleton instance
_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> Optional[CacheManager]:
    """Get or create cache manager singleton."""
    global _cache_manager
    
    if _cache_manager is None:
        try:
            database_url = os.getenv("DATABASE_URL")
            if database_url:
                _cache_manager = CacheManager(database_url)
                print("✓ Database cache initialized")
            else:
                print("⚠️  DATABASE_URL not set - caching disabled")
        except Exception as e:
            print(f"✗ Failed to initialize cache: {e}")
            _cache_manager = None
    
    return _cache_manager


if __name__ == "__main__":
    # Test database connection and create tables
    print("Testing database connection...")
    
    try:
        cache = CacheManager()
        print("✓ Database connected successfully")
        print("✓ Tables created")
        
        # Test cache operations
        print("\nTesting cache operations...")
        
        test_metrics = {
            "zScore": 2.5,
            "corr": 0.85,
            "mean": 0.0012,
            "std": 0.0045,
            "beta": 1.15,
        }
        
        test_analysis = {
            "signal": "LONG",
            "confidence": 0.78,
            "reasoning": "Test reasoning",
            "risk_level": "MEDIUM",
            "key_factors": ["factor1", "factor2"],
            "entry_recommendation": "Test recommendation"
        }
        
        # Cache test data
        cache.cache_analysis("BTC-PERP", "ETH-PERP", test_metrics, test_analysis)
        print("✓ Cached test data")
        
        # Retrieve cached data
        cached = cache.get_cached_analysis("BTC-PERP", "ETH-PERP")
        if cached:
            print("✓ Retrieved cached data")
            print(f"  Cached at: {cached['cached_at']}")
            print(f"  Expires at: {cached['expires_at']}")
        
        # Get stats
        stats = cache.get_cache_stats()
        print(f"\n✓ Cache stats: {stats}")
        
        print("\n✓ All tests passed!")
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
