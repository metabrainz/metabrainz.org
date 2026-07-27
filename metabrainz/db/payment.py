from metabrainz import db
import sqlalchemy


def list_payments(*, is_donation=None, limit=None, offset=None):

    filters = []
    filter_data = {}
    if is_donation is not None:
        filters.append("is_donation = :is_donation")
        filter_data["is_donation"] = is_donation
    where_clause = ""
    if filters:
        where_clause = "WHERE " + "AND ".join(filters)

    with db.engine.connect() as connection:
        # Performing counting before specifying limit and offset
        # (since it's a total count of items that match filters)
        count_query = sqlalchemy.text("""
            SELECT COUNT(*)
              FROM payment
            {where_clause}
        """.format(where_clause=where_clause))
        count = connection.execute(count_query, filter_data).fetchone()[0]

        filter_data["limit"] = limit
        filter_data["offset"] = offset
        query = sqlalchemy.text("""
            SELECT id,
                   is_donation,
                   amount,
                   currency,
                   first_name,
                   last_name,
                   payment_date
              FROM payment
            {where_clause}
          ORDER BY payment_date DESC
             LIMIT :limit
            OFFSET :offset
        """.format(where_clause=where_clause))
        payments = [dict(p) for p in connection.execute(query, filter_data).mappings().fetchall()]

        return payments, count
