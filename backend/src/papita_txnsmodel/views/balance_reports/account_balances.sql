WITH per_owner_account_net AS (
    SELECT
        a.owner_id,
        a.id account_id,
        a.currency,
        SUM(
            CASE
                WHEN
                    t.to_account_id = a.id AND a_to.id IS NOT NULL
                    THEN t.amount
                WHEN
                    t.from_account_id = a.id AND a_from.id IS NOT NULL
                    THEN -t.amount
                ELSE 0
            END
        ) balance,
        MAX(t.transaction_ts) last_activity_ts
    FROM papita_transactions.accounts AS a
        LEFT JOIN papita_transactions.transactions AS t
            ON
                a.owner_id = t.owner_id
                AND t.active = TRUE
                AND t.status = 'COMPLETED'
                AND (a.id = t.from_account_id OR a.id = t.to_account_id)
        LEFT JOIN papita_transactions.accounts AS a_to
            ON
                t.to_account_id = a_to.id
                AND t.owner_id = a_to.owner_id
                AND a_to.active = TRUE
        LEFT JOIN papita_transactions.accounts AS a_from
            ON
                t.from_account_id = a_from.id
                AND t.owner_id = a_from.owner_id
                AND a_from.active = TRUE
    WHERE
        a.active = TRUE
        AND (t.id IS NULL OR a_to.id IS NOT NULL OR a_from.id IS NOT NULL)
    GROUP BY a.owner_id, a.id, a.currency
)

SELECT
    owner_id,
    account_id,
    currency,
    balance,
    last_activity_ts
FROM per_owner_account_net
