from datetime import date

from flask import flash, redirect, render_template, url_for
from flask_login import current_user, login_required

from app.extensions import db
from app.features.goals import goals_bp
from app.features.goals.forms import ContributionForm, GoalForm
from app.models.goal import GoalContribution, SavingsGoal
from app.security.decorators import get_owned_or_404


@goals_bp.route("/")
@login_required
def index():
    goals = (
        SavingsGoal.query.filter_by(user_id=current_user.id)
        .order_by(SavingsGoal.is_achieved, SavingsGoal.created_at.desc())
        .all()
    )
    return render_template(
        "goals/index.html",
        goals=goals,
        contribution_form=ContributionForm(),
        today=date.today().isoformat(),
    )


@goals_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    form = GoalForm()

    if form.validate_on_submit():
        goal = SavingsGoal(
            user_id=current_user.id,
            title=form.title.data.strip(),
            target_amount=form.target_amount.data,
            target_date=form.target_date.data,
            note=(form.note.data or "").strip() or None,
        )
        db.session.add(goal)
        db.session.commit()

        flash(f'Goal "{goal.title}" created.', "success")
        return redirect(url_for("goals.index"))

    return render_template("goals/form.html", form=form, goal=None)


@goals_bp.route("/<int:goal_id>/edit", methods=["GET", "POST"])
@login_required
def edit(goal_id):
    goal = get_owned_or_404(SavingsGoal, goal_id)
    form = GoalForm(obj=goal)

    if form.validate_on_submit():
        goal.title = form.title.data.strip()
        goal.target_amount = form.target_amount.data
        goal.target_date = form.target_date.data
        goal.note = (form.note.data or "").strip() or None
        goal.refresh_status()
        db.session.commit()

        flash("Goal updated.", "success")
        return redirect(url_for("goals.index"))

    return render_template("goals/form.html", form=form, goal=goal)


@goals_bp.route("/<int:goal_id>/contribute", methods=["POST"])
@login_required
def contribute(goal_id):
    goal = get_owned_or_404(SavingsGoal, goal_id)
    form = ContributionForm()

    if form.validate_on_submit():
        db.session.add(
            GoalContribution(
                goal_id=goal.id,
                amount=form.amount.data,
                added_on=form.added_on.data,
                note=(form.note.data or "").strip() or None,
            )
        )
        db.session.flush()
        db.session.refresh(goal)

        was_achieved = goal.is_achieved
        goal.refresh_status()
        db.session.commit()

        if goal.is_achieved and not was_achieved:
            flash(f'You reached your goal "{goal.title}". Well done.', "success")
        else:
            flash("Contribution added.", "success")
    else:
        flash("That contribution could not be saved. Check the amount and date.", "danger")

    return redirect(url_for("goals.index"))


@goals_bp.route("/<int:goal_id>/delete", methods=["POST"])
@login_required
def delete(goal_id):
    goal = get_owned_or_404(SavingsGoal, goal_id)

    title = goal.title
    db.session.delete(goal)
    db.session.commit()

    flash(f'Goal "{title}" deleted.', "success")
    return redirect(url_for("goals.index"))
