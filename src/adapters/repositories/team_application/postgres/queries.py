class TeamApplicationQueries:
    INSERT_TEAM_APPLICATION = """
        INSERT INTO team_applications (
            id,
            track_id,
            name,
            status,
            rejection_reason,
            grace_deadline,
            created_at,
            updated_at
        )
        VALUES (%(id)s, %(track_id)s, %(name)s, %(status)s, %(rejection_reason)s, %(grace_deadline)s, %(created_at)s, %(updated_at)s)
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            rejection_reason = EXCLUDED.rejection_reason,
            grace_deadline = EXCLUDED.grace_deadline,
            updated_at = now()
        """

    SELECT_TEAM_APPLICATION = """
        SELECT
            t.id,
            t.track_id,
            t.name,
            t.status,
            t.rejection_reason,
            t.grace_deadline
        FROM team_applications t
        WHERE t.id = %(id)s
        """

    SELECT_TEAM_APPLICATION_BY_TRACK_ID = """
        SELECT
            t.id,
            t.track_id,
            t.name,
            t.status,
            t.rejection_reason,
            t.grace_deadline
        FROM team_applications t
        WHERE t.track_id = %(track_id)s
        """

    SELECT_CONFIRMED_BY_TRACK_ID = """
        SELECT
            t.id,
            t.track_id,
            t.name,
            t.status,
            t.rejection_reason,
            t.grace_deadline
        FROM team_applications t
        WHERE t.track_id = %(track_id)s
        AND t.status = 'confirmed'
        """

    SELECT_EXPIRED_INVALID = """
        SELECT
            t.id,
            t.track_id,
            t.name,
            t.status,
            t.rejection_reason,
            t.grace_deadline
        FROM team_applications t
        WHERE t.status = 'invalid'
        AND t.grace_deadline < now()
        """

    COUNT_CONFIRMED_APPLICATIONS_BY_ID = """
        SELECT COUNT (*)
        FROM team_applications t
        WHERE t.track_id = %(track_id)s
        AND t.status = 'confirmed'
        """

    SELECT_NEXT_TEAM_APPLICATION = """
        SELECT
            t.id,
            t.track_id,
            t.name,
            t.status,
            t.rejection_reason,
            t.grace_deadline
        FROM team_applications t
        WHERE t.track_id = %(track_id)s
        AND t.status = 'validated'
        ORDER BY t.updated_at ASC
        LIMIT 1
        """


class MembersQueries:
    INSERT_MEMBER = """
        INSERT INTO members (
            id,
            name,
            surname,
            patronymic,
            role_id,
            created_at
        )
        VALUES (%(id)s, %(name)s, %(surname)s, %(patronymic)s, %(role_id)s, %(created_at)s)
        ON CONFLICT (id) DO NOTHING
        """

    DELETE_OLD_MEMBER_CONNECTION = """
        DELETE FROM team_application_members
        WHERE application_id = %(application_id)s
        """

    INSERT_MEMBER_CONNECTION = """
        INSERT INTO team_application_members (
            application_id,
            member_id
        )
        VALUES (%(application_id)s, %(member_id)s)
        ON CONFLICT (application_id, member_id) DO NOTHING
        """

    SELECT_MEMBERS = """
        SELECT
            m.id,
            m.name,
            m.surname,
            m.patronymic,
            m.role_id
        FROM members m
        JOIN team_application_members tm ON tm.member_id = m.id
        WHERE tm.application_id = %(application_id)s
        """

    SELECT_MEMBERS_BY_APPLICATION_IDS = """
        SELECT
            m.id,
            m.name,
            m.surname,
            m.patronymic,
            m.role_id,
            tm.application_id
        FROM members m
        JOIN team_application_members tm ON tm.member_id = m.id
        WHERE tm.application_id = ANY(%(application_ids)s)
        """


class OutboxQueries:
    INSERT_OUTBOX_EVENT = """
        INSERT INTO outbox_events (
            id,
            aggregate_type,
            aggregate_id,
            event_type,
            payload,
            idempotency_key
        )
        VALUES (%(id)s, %(aggregate_type)s, %(aggregate_id)s, %(event_type)s, %(payload)s, %(idempotency_key)s)
        ON CONFLICT (idempotency_key) DO NOTHING
        """
