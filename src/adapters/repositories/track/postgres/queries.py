class TrackQueries:
    INSERT_TRACK = """
        INSERT INTO tracks (
            id,
            name,
            max_team_count,
            auto_confirm,
            grace_period_hours,
            created_at,
            updated_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """

    INSERT_CONFIRMATION_RULE = """
        INSERT INTO track_confirmation_rules (
            id,
            track_id,
            rule_type,
            params,
            sort_order
        )
        VALUES (%s, %s, %s, %s, %s)
        """

    INSERT_ROLE = """
        INSERT INTO roles (
            id,
            name,
            count,
            created_at
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """

    INSERT_ROLE_CONNECTION = """
        INSERT INTO track_roles (
            track_id,
            role_id
        )
        VALUES (%s, %s)
        ON CONFLICT (track_id, role_id) DO NOTHING
        """

    SELECT_TRACK = """
        SELECT
            t.name,
            t.max_team_count,
            t.auto_confirm,
            t.grace_period_hours
        FROM tracks t
        WHERE id = %s
        """

    SELECT_RULES = """
        SELECT
            r.rule_type,
            r.params
        FROM track_confirmation_rules r
        WHERE r.track_id = %s
        ORDER BY sort_order ASC
        """

    SELECT_ROLES = """
        SELECT r.id, r.name, r.count
        FROM roles r
        JOIN track_roles tr ON tr.role_id = r.id
        WHERE tr.track_id = %s
        """
