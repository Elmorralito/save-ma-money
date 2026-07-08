WITH owner_biannual_net AS (
    SELECT
        t.owner_id,
        t.currency,
        EXTRACT(YEAR FROM t.transaction_ts)::INTEGER balance_year,
        CASE
            WHEN EXTRACT(MONTH FROM t.transaction_ts) <= 6 THEN 1
            ELSE 2
        END balance_half,
        SUM(
            CASE
                WHEN
                    t.to_account_id IS NOT NULL AND a_to.id IS NOT NULL
                    THEN t.amount
                ELSE 0
            END
        ) - SUM(
            CASE
                WHEN
                    t.from_account_id IS NOT NULL AND a_from.id IS NOT NULL
                    THEN t.amount
                ELSE 0
            END
        ) biannual_net_change
    FROM papita_transactions.transactions AS t
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
        t.status = 'COMPLETED'
        AND t.active = TRUE
        AND (a_to.id IS NOT NULL OR a_from.id IS NOT NULL)
    GROUP BY t.owner_id, balance_year, balance_half, t.currency
)

SELECT
    owner_id,
    balance_year,
    balance_half,
    currency,
    biannual_net_change,
    SUM(biannual_net_change) OVER (
        PARTITION BY owner_id, currency
        ORDER BY balance_year, balance_half
        ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) total_balance
FROM owner_biannual_net
