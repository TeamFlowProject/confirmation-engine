class TrackQueries:
    INSERT_TRACK = """
        INSERT INTO tracks (
            id,
            name,
            max_team_count,
            auto_confirm,
            grace_period_hours,
            confirmation_rules,
            created_at,
            updated_at
        )
        VALUES (%(id)s, %(name)s, %(max_team_count)s, %(auto_confirm)s, %(grace_period_hours)s, %(confirmation_rules)s::jsonb, %(created_at)s, %(updated_at)s)
        ON CONFLICT (id) DO UPDATE SET
            name               = EXCLUDED.name,
            max_team_count     = EXCLUDED.max_team_count,
            auto_confirm       = EXCLUDED.auto_confirm,
            grace_period_hours = EXCLUDED.grace_period_hours,
            confirmation_rules = EXCLUDED.confirmation_rules,
            updated_at         = now()
        """

    SELECT_TRACK = """
        SELECT
            t.name,
            t.max_team_count,
            t.auto_confirm,
            t.grace_period_hours,
            t.confirmation_rules
        FROM tracks t
        WHERE t.id = %(id)s
        """


class RolesQueries:
    INSERT_ROLE = """
        INSERT INTO roles (
            id,
            name,
            count,
            created_at
        )
        VALUES (%(id)s, %(name)s, %(count)s, %(created_at)s)
        ON CONFLICT (id) DO NOTHING
        """

    INSERT_ROLE_CONNECTION = """
        INSERT INTO track_roles (
            track_id,
            role_id
        )
        VALUES (%(track_id)s, %(role_id)s)
        ON CONFLICT (track_id, role_id) DO NOTHING
        """

    SELECT_ROLES = """
        SELECT r.id, r.name, r.count
        FROM roles r
        JOIN track_roles tr ON tr.role_id = r.id
        WHERE tr.track_id = %(track_id)s
        """

    DELETE_TRACK_ROLES = """
        DELETE FROM track_roles
        WHERE track_id = %(track_id)s
        """
