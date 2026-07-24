from flask import abort
from flask_login import current_user


def get_owned_or_404(model, record_id):
    record = db_get(model, record_id)
    if record is None or record.user_id != current_user.id:
        abort(404)
    return record


def db_get(model, record_id):
    return model.query.get(record_id)
