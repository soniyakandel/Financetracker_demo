from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.features.recurring import recurring_bp
from app.features.recurring.forms import RecurringForm
from app.models.category import Category
from app.models.recurring import RecurringExpense
from app.security.decorators import get_owned_or_404


def _user_categories():
    return (
        Category.query.filter_by(user_id=current_user.id)
        .order_by(Category.is_default.desc(), Category.name)
        .all()
    )


@recurring_bp.route("/")
@login_required
def index():
    rules = (
        RecurringExpense.query.filter_by(user_id=current_user.id)
        .order_by(RecurringExpense.is_active.desc(), RecurringExpense.next_due_on)
        .all()
    )
    return render_template("recurring/index.html", rules=rules)


@recurring_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = RecurringForm()
    form.set_category_choices(_user_categories())

    if form.validate_on_submit():
        rule = RecurringExpense(
            user_id=current_user.id,
            category_id=form.category_id.data,
            title=form.title.data.strip(),
            amount=form.amount.data,
            frequency=form.frequency.data,
            start_on=form.start_on.data,
            next_due_on=form.start_on.data,
        )
        db.session.add(rule)
        db.session.commit()

        flash(f'"{rule.title}" will now be added automatically.', "success")
        return redirect(url_for("recurring.index"))

    return render_template("recurring/form.html", form=form, rule=None)


@recurring_bp.route("/<int:rule_id>/edit", methods=["GET", "POST"])
@login_required
def edit(rule_id):
    rule = get_owned_or_404(RecurringExpense, rule_id)

    form = RecurringForm(obj=rule)
    form.set_category_choices(_user_categories())

    if form.validate_on_submit():
        if form.start_on.data != rule.start_on:
            rule.next_due_on = form.start_on.data

        rule.title = form.title.data.strip()
        rule.amount = form.amount.data
        rule.category_id = form.category_id.data
        rule.frequency = form.frequency.data
        rule.start_on = form.start_on.data
        db.session.commit()

        flash("Recurring expense updated.", "success")
        return redirect(url_for("recurring.index"))

    return render_template("recurring/form.html", form=form, rule=rule)


@recurring_bp.route("/<int:rule_id>/toggle", methods=["POST"])
@login_required
def toggle(rule_id):
    rule = get_owned_or_404(RecurringExpense, rule_id)
    rule.is_active = not rule.is_active
    db.session.commit()

    flash(
        f'"{rule.title}" is now {"active" if rule.is_active else "paused"}.',
        "success",
    )
    return redirect(url_for("recurring.index"))


@recurring_bp.route("/<int:rule_id>/delete", methods=["POST"])
@login_required
def delete(rule_id):
    rule = get_owned_or_404(RecurringExpense, rule_id)

    title = rule.title
    db.session.delete(rule)
    db.session.commit()

    flash(f'"{title}" removed. Past entries were kept.', "success")
    return redirect(url_for("recurring.index"))
