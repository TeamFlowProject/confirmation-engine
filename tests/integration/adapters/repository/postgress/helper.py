async def cleanup_db(pool):
    async with pool.connection() as conn:
        await conn.execute("DELETE FROM team_application_members")
        await conn.execute("DELETE FROM team_applications")
        await conn.execute("DELETE FROM track_roles")
        await conn.execute("DELETE FROM track_confirmation_rules")
        await conn.execute("DELETE FROM tracks")
        await conn.execute("DELETE FROM members")
        await conn.execute("DELETE FROM roles")
