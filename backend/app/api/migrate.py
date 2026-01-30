"""Database migration endpoint."""

from fastapi import APIRouter, HTTPException
from sqlalchemy import text
from app.core.database import get_async_session

router = APIRouter(prefix="/migrate", tags=["migrate"])


@router.post("/add-user-id-column")
async def add_user_id_column():
    """Add user_id column to chat_sessions if missing."""
    async for session in get_async_session():
        try:
            # Check if column exists
            check_sql = text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'chat_sessions' AND column_name = 'user_id'
            """)
            result = await session.execute(check_sql)
            exists = result.fetchone()

            if exists:
                return {"status": "ok", "message": "Column user_id already exists"}

            # Add the column
            alter_sql = text("""
                ALTER TABLE chat_sessions
                ADD COLUMN user_id VARCHAR(50) REFERENCES users(id) ON DELETE CASCADE
            """)
            await session.execute(alter_sql)

            # Create index
            index_sql = text("""
                CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON chat_sessions(user_id)
            """)
            await session.execute(index_sql)

            await session.commit()

            return {"status": "ok", "message": "Column user_id added successfully"}

        except Exception as e:
            await session.rollback()
            raise HTTPException(status_code=500, detail=f"Migration failed: {str(e)}")
