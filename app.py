from flask import (

    Flask,

    render_template,

    request,

    redirect,

    url_for,

    flash,

    session

)

from werkzeug.security import (

    generate_password_hash,

    check_password_hash

)

from dotenv import load_dotenv

from datetime import date

import os

from database import get_db_connection

load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv("SECRET_KEY")

# ==================================================

# HOME

# ==================================================

@app.route("/")

def home():

    if "user_id" in session:

        return redirect(url_for("dashboard"))

    return redirect(url_for("login"))

# ==================================================

# REGISTER

# ==================================================

@app.route("/register", methods=["GET", "POST"])

def register():

    if "user_id" in session:

        return redirect(url_for("dashboard"))

    if request.method == "POST":

        name = request.form.get("name", "").strip()

        email = request.form.get(

            "email",

            ""

        ).strip().lower()

        password = request.form.get(

            "password",

            ""

        )

        if not name or not email or not password:

            flash(

                "All fields are required.",

                "error"

            )

            return redirect(url_for("register"))

        if len(password) < 6:

            flash(

                "Password must contain at least 6 characters.",

                "error"

            )

            return redirect(url_for("register"))

        connection = None

        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor()

            cursor.execute(

                """

                SELECT user_id

                FROM users

                WHERE email = %s

                """,

                (email,)

            )

            existing_user = cursor.fetchone()

            if existing_user:

                flash(

                    "An account with this email already exists.",

                    "error"

                )

                return redirect(url_for("register"))

            password_hash = generate_password_hash(password)

            cursor.execute(

                """

                INSERT INTO users

                (

                    name,

                    email,

                    password_hash

                )

                VALUES

                (

                    %s,

                    %s,

                    %s

                )

                """,

                (

                    name,

                    email,

                    password_hash

                )

            )

            connection.commit()

            flash(

                "Account created successfully. Please login.",

                "success"

            )

            return redirect(url_for("login"))

        except Exception as error:

            print("Registration error:", error)

            flash(

                "Something went wrong while creating your account.",

                "error"

            )

        finally:

            if cursor:

                cursor.close()

            if connection:

                connection.close()

    return render_template("register.html")

# ==================================================

# LOGIN

# ==================================================

@app.route("/login", methods=["GET", "POST"])

def login():

    if "user_id" in session:

        return redirect(url_for("dashboard"))

    if request.method == "POST":

        email = request.form.get(

            "email",

            ""

        ).strip().lower()

        password = request.form.get(

            "password",

            ""

        )

        if not email or not password:

            flash(

                "Email and password are required.",

                "error"

            )

            return redirect(url_for("login"))

        connection = None

        cursor = None

        try:

            connection = get_db_connection()

            cursor = connection.cursor(

                dictionary=True

            )

            cursor.execute(

                """

                SELECT

                    user_id,

                    name,

                    email,

                    password_hash

                FROM users

                WHERE email = %s

                """,

                (email,)

            )

            user = cursor.fetchone()

            if user and check_password_hash(

                user["password_hash"],

                password

            ):

                session["user_id"] = user["user_id"]

                session["user_name"] = user["name"]

                return redirect(url_for("dashboard"))

            flash(

                "Invalid email or password.",

                "error"

            )

        except Exception as error:

            print("Login error:", error)

            flash(

                "Something went wrong while logging in.",

                "error"

            )

        finally:

            if cursor:

                cursor.close()

            if connection:

                connection.close()

    return render_template("login.html")

# ==================================================

# LOGOUT

# ==================================================

@app.route("/logout")

def logout():

    session.clear()

    flash(

        "You have been logged out.",

        "success"

    )

    return redirect(url_for("login"))

# ==================================================

# DASHBOARD

# ==================================================

@app.route("/dashboard")

def dashboard():

    if "user_id" not in session:

        return redirect(url_for("login"))

    connection = None

    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(

            dictionary=True

        )

        user_id = session["user_id"]

        today = date.today()

        current_month = today.month

        current_year = today.year

        # ==========================================

        # TOTAL INCOME

        # ==========================================

        cursor.execute(

            """

            SELECT

                COALESCE(

                    SUM(t.amount),

                    0

                ) AS total

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'income'

            """,

            (user_id,)

        )

        total_income = cursor.fetchone()["total"]

        # ==========================================

        # TOTAL EXPENSES

        # ==========================================

        cursor.execute(

            """

            SELECT

                COALESCE(

                    SUM(t.amount),

                    0

                ) AS total

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'expense'

            """,

            (user_id,)

        )

        total_expenses = cursor.fetchone()["total"]

        # ==========================================

        # BALANCE

        # ==========================================

        balance = total_income - total_expenses

        # ==========================================

        # MONTHLY INCOME

        # ==========================================

        cursor.execute(

            """

            SELECT

                COALESCE(

                    SUM(t.amount),

                    0

                ) AS total

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'income'

            AND MONTH(t.transaction_date) = %s

            AND YEAR(t.transaction_date) = %s

            """,

            (

                user_id,

                current_month,

                current_year

            )

        )

        monthly_income = cursor.fetchone()["total"]

        # ==========================================

        # MONTHLY EXPENSES

        # ==========================================

        cursor.execute(

            """

            SELECT

                COALESCE(

                    SUM(t.amount),

                    0

                ) AS total

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'expense'

            AND MONTH(t.transaction_date) = %s

            AND YEAR(t.transaction_date) = %s

            """,

            (

                user_id,

                current_month,

                current_year

            )

        )

        monthly_expenses = cursor.fetchone()["total"]

        # ==========================================

        # MONTHLY BUDGET

        # ==========================================

        cursor.execute(

            """

            SELECT

                COALESCE(

                    SUM(amount),

                    0

                ) AS total

            FROM budgets

            WHERE user_id = %s

            AND month = %s

            AND year = %s

            """,

            (

                user_id,

                current_month,

                current_year

            )

        )

        monthly_budget = cursor.fetchone()["total"]

        # ==========================================

        # BUDGET REMAINING

        # ==========================================

        budget_remaining = (

            monthly_budget -

            monthly_expenses

        )

        # ==========================================

        # BUDGET PERCENTAGE

        # ==========================================

        if monthly_budget > 0:

            budget_percentage = (

                monthly_expenses /

                monthly_budget

            ) * 100

        else:

            budget_percentage = 0

        display_percentage = min(

            budget_percentage,

            100

        )

        # ==========================================

        # RECENT INCOME

        cursor.execute(
            """
            SELECT
                t.transaction_id,
                t.amount,
                t.description,
                t.transaction_date,
                t.payment_method,
                c.name AS category_name
            FROM transactions t
            JOIN categories c
                ON t.category_id = c.category_id
            WHERE t.user_id = %s
            AND c.type = 'income'
            ORDER BY
                t.transaction_date DESC,
                t.transaction_id DESC
            LIMIT 5
            """,
            (user_id,)
        )

        recent_income = cursor.fetchall()

        # RECENT EXPENSES

        # ==========================================

        cursor.execute(

            """

            SELECT

                t.transaction_id,

                t.amount,

                t.description,

                t.transaction_date,

                t.payment_method,

                c.name AS category_name

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'expense'

            ORDER BY

                t.transaction_date DESC,

                t.transaction_id DESC

            LIMIT 5

            """,

            (user_id,)

        )

        recent_expenses = cursor.fetchall()

        # ==========================================

        # EXPENSES BY CATEGORY

        # ==========================================

        cursor.execute(

            """

            SELECT

                c.name AS category_name,

                COALESCE(

                    SUM(t.amount),

                    0

                ) AS total

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'expense'

            GROUP BY

                c.category_id,

                c.name

            ORDER BY

                total DESC

            """,

            (user_id,)

        )

        category_expenses = cursor.fetchall()

        # ==========================================

        # CURRENT MONTH EXPENSES BY CATEGORY

        # ==========================================

        cursor.execute(

            """

            SELECT

                c.name AS category_name,

                COALESCE(

                    SUM(t.amount),

                    0

                ) AS total

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'expense'

            AND MONTH(t.transaction_date) = %s

            AND YEAR(t.transaction_date) = %s

            GROUP BY

                c.category_id,

                c.name

            ORDER BY

                total DESC

            """,

            (

                user_id,

                current_month,

                current_year

            )

        )

        monthly_category_expenses = cursor.fetchall()

        # ==========================================

        # HIGHEST SPENDING CATEGORY

        # ==========================================

        if monthly_category_expenses:

            highest_category = (

                monthly_category_expenses[0]["category_name"]

            )

            highest_category_amount = (

                monthly_category_expenses[0]["total"]

            )

        else:

            highest_category = "No spending yet"

            highest_category_amount = 0

        # ==========================================

        # AVERAGE DAILY SPENDING

        # ==========================================

        if today.day > 0:

            average_daily_spending = (

                monthly_expenses / today.day

            )

        else:

            average_daily_spending = 0

        # ==========================================

        # SIX MONTH TREND

        # ==========================================

        month_data = []

        year = current_year

        month = current_month

        for _ in range(6):

            month_data.append(

                {

                    "year": year,

                    "month": month

                }

            )

            month -= 1

            if month == 0:

                month = 12

                year -= 1

        month_data.reverse()

        monthly_trend_labels = []

        monthly_trend_income = []

        monthly_trend_expenses = []

        for item in month_data:

            trend_year = item["year"]

            trend_month = item["month"]

            cursor.execute(

                """

                SELECT

                    COALESCE(

                        SUM(

                            CASE

                                WHEN c.type = 'income'

                                THEN t.amount

                                ELSE 0

                            END

                        ),

                        0

                    ) AS income,

                    COALESCE(

                        SUM(

                            CASE

                                WHEN c.type = 'expense'

                                THEN t.amount

                                ELSE 0

                            END

                        ),

                        0

                    ) AS expenses

                FROM transactions t

                JOIN categories c

                    ON t.category_id = c.category_id

                WHERE t.user_id = %s

                AND MONTH(t.transaction_date) = %s

                AND YEAR(t.transaction_date) = %s

                """,

                (

                    user_id,

                    trend_month,

                    trend_year

                )

            )

            trend_result = cursor.fetchone()

            month_names = [

                "Jan",

                "Feb",

                "Mar",

                "Apr",

                "May",

                "Jun",

                "Jul",

                "Aug",

                "Sep",

                "Oct",

                "Nov",

                "Dec"

            ]

            monthly_trend_labels.append(

                month_names[trend_month - 1]

            )

            monthly_trend_income.append(

                float(trend_result["income"])

            )

            monthly_trend_expenses.append(

                float(trend_result["expenses"])

            )

        # ==========================================

        # BUDGET STATUS

        # ==========================================

        if monthly_budget <= 0:

            budget_status = "No budget set"

        elif budget_remaining < 0:

            budget_status = "Over budget"

        elif budget_percentage >= 80:

            budget_status = "Budget almost reached"

        else:

            budget_status = "Within budget"

        # ==========================================

        # SPENDING INSIGHT

        # ==========================================

        if monthly_expenses == 0:

            spending_insight = (

                "You haven't recorded any expenses this month yet."

            )

        elif monthly_budget > 0 and budget_remaining < 0:

            spending_insight = (

                f"You are ₹{abs(float(budget_remaining)):.2f} "

                f"over your monthly budget. "

                f"Try reducing spending on {highest_category}."

            )

        elif monthly_budget > 0 and budget_percentage >= 80:

            spending_insight = (

                f"You have used {budget_percentage:.0f}% "

                f"of your monthly budget. "

                f"{highest_category} is your highest spending category."

            )

        else:

            spending_insight = (

                f"{highest_category} is your highest spending category "

                f"this month at ₹{float(highest_category_amount):.2f}. "

                f"Your average daily spending is "

                f"₹{float(average_daily_spending):.2f}."

            )

        # ==========================================

        # DASHBOARD

        # ==========================================

        return render_template(

            "dashboard.html",

            user_name=session["user_name"],

            total_income=total_income,

            total_expenses=total_expenses,

            balance=balance,

            monthly_income=monthly_income,

            monthly_expenses=monthly_expenses,

            monthly_budget=monthly_budget,

            budget_remaining=budget_remaining,

            budget_percentage=budget_percentage,

            display_percentage=display_percentage,

            recent_expenses=recent_expenses,
            recent_income=recent_income,
            category_expenses=category_expenses,

            monthly_category_expenses=monthly_category_expenses,

            highest_category=highest_category,

            highest_category_amount=highest_category_amount,

            average_daily_spending=average_daily_spending,

            monthly_trend_labels=monthly_trend_labels,

            monthly_trend_income=monthly_trend_income,

            monthly_trend_expenses=monthly_trend_expenses,

            budget_status=budget_status,

            spending_insight=spending_insight

        )

    except Exception as error:

        print(

            "Dashboard error:",

            error

        )

        flash(

            "Unable to load dashboard.",

            "error"

        )

        return redirect(url_for("login"))

    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()

# ==================================================

# ADD EXPENSE

# ==================================================

@app.route(

    "/add-expense",

    methods=["GET", "POST"]

)

def add_expense():

    if "user_id" not in session:

        return redirect(url_for("login"))

    connection = None

    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(

            dictionary=True

        )

        user_id = session["user_id"]

        cursor.execute(

            """

            SELECT

                category_id,

                name

            FROM categories

            WHERE type = 'expense'

            AND (

                user_id IS NULL

                OR user_id = %s

            )

            ORDER BY name

            """,

            (user_id,)

        )

        categories = cursor.fetchall()

        if request.method == "POST":

            amount = request.form.get("amount")

            category_id = request.form.get(

                "category_id"

            )

            description = request.form.get(

                "description",

                ""

            ).strip()

            transaction_date = request.form.get(

                "transaction_date"

            )

            payment_method = request.form.get(

                "payment_method"

            )

            if not amount or not category_id:

                flash(

                    "Amount and category are required.",

                    "error"

                )

                return redirect(url_for("add_expense"))

            cursor.execute(

                """

                INSERT INTO transactions

                (

                    user_id,

                    category_id,

                    amount,

                    description,

                    transaction_date,

                    payment_method

                )

                VALUES

                (

                    %s,

                    %s,

                    %s,

                    %s,

                    %s,

                    %s

                )

                """,

                (

                    user_id,

                    category_id,

                    amount,

                    description,

                    transaction_date,

                    payment_method

                )

            )

            connection.commit()

            flash(

                "Expense added successfully!",

                "success"

            )

            return redirect(url_for("dashboard"))

        return render_template(

            "add_expense.html",

            categories=categories

        )

    except Exception as error:

        print(

            "Expense error:",

            error

        )

        flash(

            "Something went wrong while adding the expense.",

            "error"

        )

        return redirect(url_for("dashboard"))

    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()

# ==================================================

# ADD INCOME

# ==================================================

@app.route(

    "/add-income",

    methods=["GET", "POST"]

)

def add_income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT category_id, name
            FROM categories
            WHERE type = 'income'
            AND (user_id IS NULL OR user_id = %s)
            ORDER BY name
            """,
            (user_id,)
        )
        categories = cursor.fetchall()

        if request.method == "POST":
            amount = request.form.get("amount", "").strip()
            category_id = request.form.get("category_id", "").strip()
            description = request.form.get("description", "").strip()
            transaction_date = request.form.get("transaction_date", "").strip()
            payment_method = request.form.get("payment_method", "").strip()

            if not amount or not category_id:
                flash("Amount and category are required.", "error")
                return redirect(url_for("add_income"))

            try:
                amount_value = float(amount)
                if amount_value <= 0:
                    raise ValueError
            except ValueError:
                flash("Amount must be greater than zero.", "error")
                return redirect(url_for("add_income"))

            if not transaction_date:
                transaction_date = date.today().isoformat()

            if not payment_method:
                payment_method = "Other"

            cursor.execute(
                """
                SELECT category_id
                FROM categories
                WHERE category_id = %s
                AND type = 'income'
                AND (user_id IS NULL OR user_id = %s)
                """,
                (category_id, user_id)
            )

            if not cursor.fetchone():
                flash("Please select a valid income category.", "error")
                return redirect(url_for("add_income"))

            cursor.execute(
                """
                INSERT INTO transactions
                (
                    user_id,
                    category_id,
                    amount,
                    description,
                    transaction_date,
                    payment_method
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    category_id,
                    amount_value,
                    description,
                    transaction_date,
                    payment_method
                )
            )

            connection.commit()
            flash("Income added successfully!", "success")
            return redirect(url_for("dashboard"))

        return render_template(
            "add_income.html",
            categories=categories,
            today=date.today().isoformat()
        )

    except Exception as error:
        if connection:
            connection.rollback()

        print("Income error:", error)
        flash(f"Unable to add income: {error}", "error")
        return redirect(url_for("add_income"))

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()

# INCOME HISTORY
# ==================================================

@app.route("/income")
def income():
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        user_id = session["user_id"]

        search = request.args.get("search", "").strip()
        category_id = request.args.get("category", "")
        date_from = request.args.get("date_from", "")
        date_to = request.args.get("date_to", "")

        cursor.execute(
            """
            SELECT category_id, name
            FROM categories
            WHERE type = 'income'
            AND (user_id IS NULL OR user_id = %s)
            ORDER BY name
            """,
            (user_id,)
        )
        categories = cursor.fetchall()

        query = """
            SELECT
                t.transaction_id,
                t.amount,
                t.description,
                t.transaction_date,
                t.payment_method,
                c.category_id,
                c.name AS category_name
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.user_id = %s
            AND c.type = 'income'
        """

        params = [user_id]

        if search:
            query += """
                AND (
                    t.description LIKE %s
                    OR c.name LIKE %s
                    OR t.payment_method LIKE %s
                )
            """
            search_value = f"%{search}%"
            params.extend([
                search_value,
                search_value,
                search_value
            ])

        if category_id:
            query += " AND t.category_id = %s"
            params.append(category_id)

        if date_from:
            query += " AND t.transaction_date >= %s"
            params.append(date_from)

        if date_to:
            query += " AND t.transaction_date <= %s"
            params.append(date_to)

        query += """
            ORDER BY
                t.transaction_date DESC,
                t.transaction_id DESC
        """

        cursor.execute(query, tuple(params))
        income_list = cursor.fetchall()

        filtered_total = sum(
            float(item["amount"])
            for item in income_list
        )

        return render_template(
            "income.html",
            incomes=income_list,
            categories=categories,
            search=search,
            selected_category=category_id,
            date_from=date_from,
            date_to=date_to,
            filtered_total=filtered_total
        )

    except Exception as error:
        print("Income history error:", error)
        flash("Unable to load income history.", "error")
        return redirect(url_for("dashboard"))

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

# ==================================================
# EDIT INCOME
# ==================================================

@app.route(
    "/edit-income/<int:transaction_id>",
    methods=["GET", "POST"]
)
def edit_income(transaction_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor(dictionary=True)
        user_id = session["user_id"]

        cursor.execute(
            """
            SELECT
                t.transaction_id,
                t.amount,
                t.description,
                t.transaction_date,
                t.payment_method,
                t.category_id
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.transaction_id = %s
            AND t.user_id = %s
            AND c.type = 'income'
            """,
            (
                transaction_id,
                user_id
            )
        )

        income_item = cursor.fetchone()

        if not income_item:
            flash(
                "Income transaction not found.",
                "error"
            )
            return redirect(url_for("income"))

        cursor.execute(
            """
            SELECT category_id, name
            FROM categories
            WHERE type = 'income'
            AND (user_id IS NULL OR user_id = %s)
            ORDER BY name
            """,
            (user_id,)
        )

        categories = cursor.fetchall()

        if request.method == "POST":
            amount = request.form.get("amount")
            category_id = request.form.get("category_id")
            description = request.form.get(
                "description",
                ""
            ).strip()
            transaction_date = request.form.get(
                "transaction_date"
            )
            payment_method = request.form.get(
                "payment_method"
            )

            if not amount or not category_id:
                flash(
                    "Amount and category are required.",
                    "error"
                )
                return redirect(
                    url_for(
                        "edit_income",
                        transaction_id=transaction_id
                    )
                )

            try:
                amount_value = float(amount)

                if amount_value <= 0:
                    raise ValueError

            except ValueError:
                flash(
                    "Amount must be greater than zero.",
                    "error"
                )
                return redirect(
                    url_for(
                        "edit_income",
                        transaction_id=transaction_id
                    )
                )

            cursor.execute(
                """
                SELECT category_id
                FROM categories
                WHERE category_id = %s
                AND type = 'income'
                AND (user_id IS NULL OR user_id = %s)
                """,
                (
                    category_id,
                    user_id
                )
            )

            if not cursor.fetchone():
                flash(
                    "Invalid income category.",
                    "error"
                )
                return redirect(
                    url_for(
                        "edit_income",
                        transaction_id=transaction_id
                    )
                )

            cursor.execute(
                """
                UPDATE transactions
                SET
                    category_id = %s,
                    amount = %s,
                    description = %s,
                    transaction_date = %s,
                    payment_method = %s
                WHERE transaction_id = %s
                AND user_id = %s
                """,
                (
                    category_id,
                    amount,
                    description,
                    transaction_date,
                    payment_method,
                    transaction_id,
                    user_id
                )
            )

            connection.commit()

            flash(
                "Income updated successfully!",
                "success"
            )

            return redirect(url_for("income"))

        return render_template(
            "edit_income.html",
            income=income_item,
            categories=categories
        )

    except Exception as error:
        print("Edit income error:", error)

        flash(
            "Unable to edit income.",
            "error"
        )

        return redirect(url_for("income"))

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

# ==================================================
# DELETE INCOME
# ==================================================

@app.route(
    "/delete-income/<int:transaction_id>",
    methods=["POST"]
)
def delete_income(transaction_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    connection = None
    cursor = None

    try:
        connection = get_db_connection()
        cursor = connection.cursor()

        user_id = session["user_id"]

        cursor.execute(
            """
            DELETE t
            FROM transactions t
            JOIN categories c
                ON t.category_id = c.category_id
            WHERE t.transaction_id = %s
            AND t.user_id = %s
            AND c.type = 'income'
            """,
            (
                transaction_id,
                user_id
            )
        )

        connection.commit()

        if cursor.rowcount == 0:
            flash(
                "Income transaction not found.",
                "error"
            )
        else:
            flash(
                "Income deleted successfully.",
                "success"
            )

        return redirect(url_for("income"))

    except Exception as error:
        print("Delete income error:", error)

        flash(
            "Unable to delete income.",
            "error"
        )

        return redirect(url_for("income"))

    finally:
        if cursor:
            cursor.close()

        if connection:
            connection.close()

# SET MONTHLY BUDGET

# ==================================================

@app.route(

    "/budget",

    methods=["GET", "POST"]

)

def budget():

    if "user_id" not in session:

        return redirect(url_for("login"))

    connection = None

    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(

            dictionary=True

        )

        user_id = session["user_id"]

        today = date.today()

        current_month = today.month

        current_year = today.year

        if request.method == "POST":

            amount = request.form.get("amount")

            month = request.form.get("month")

            year = request.form.get("year")

            if not amount or not month or not year:

                flash(

                    "All budget fields are required.",

                    "error"

                )

                return redirect(url_for("budget"))

            cursor.execute(

                """

                SELECT

                    budget_id

                FROM budgets

                WHERE user_id = %s

                AND category_id IS NULL

                AND month = %s

                AND year = %s

                """,

                (

                    user_id,

                    month,

                    year

                )

            )

            existing_budget = cursor.fetchone()

            if existing_budget:

                cursor.execute(

                    """

                    UPDATE budgets

                    SET amount = %s

                    WHERE budget_id = %s

                    AND user_id = %s

                    """,

                    (

                        amount,

                        existing_budget["budget_id"],

                        user_id

                    )

                )

            else:

                cursor.execute(

                    """

                    INSERT INTO budgets

                    (

                        user_id,

                        category_id,

                        amount,

                        month,

                        year

                    )

                    VALUES

                    (

                        %s,

                        NULL,

                        %s,

                        %s,

                        %s

                    )

                    """,

                    (

                        user_id,

                        amount,

                        month,

                        year

                    )

                )

            connection.commit()

            flash(

                "Monthly budget saved successfully!",

                "success"

            )

            return redirect(url_for("budget"))

        cursor.execute(

            """

            SELECT

                amount

            FROM budgets

            WHERE user_id = %s

            AND category_id IS NULL

            AND month = %s

            AND year = %s

            """,

            (

                user_id,

                current_month,

                current_year

            )

        )

        current_budget = cursor.fetchone()

        return render_template(

            "budget.html",

            current_budget=current_budget,

            current_month=current_month,

            current_year=current_year

        )

    except Exception as error:

        print(

            "Budget error:",

            error

        )

        flash(

            "Unable to manage your budget.",

            "error"

        )

        return redirect(url_for("dashboard"))

    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()

# ==================================================

# EXPENSE HISTORY

# ==================================================

@app.route("/expenses")

def expenses():

    if "user_id" not in session:

        return redirect(url_for("login"))

    connection = None

    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(

            dictionary=True

        )

        user_id = session["user_id"]

        search = request.args.get(

            "search",

            ""

        ).strip()

        category_id = request.args.get(

            "category",

            ""

        )

        date_from = request.args.get(

            "date_from",

            ""

        )

        date_to = request.args.get(

            "date_to",

            ""

        )

        cursor.execute(

            """

            SELECT

                category_id,

                name

            FROM categories

            WHERE type = 'expense'

            AND (

                user_id IS NULL

                OR user_id = %s

            )

            ORDER BY name

            """,

            (user_id,)

        )

        categories = cursor.fetchall()

        query = """

            SELECT

                t.transaction_id,

                t.amount,

                t.description,

                t.transaction_date,

                t.payment_method,

                c.category_id,

                c.name AS category_name

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.user_id = %s

            AND c.type = 'expense'

        """

        params = [user_id]

        if search:

            query += """

                AND (

                    t.description LIKE %s

                    OR c.name LIKE %s

                    OR t.payment_method LIKE %s

                )

            """

            search_value = f"%{search}%"

            params.extend([

                search_value,

                search_value,

                search_value

            ])

        if category_id:

            query += """

                AND t.category_id = %s

            """

            params.append(category_id)

        if date_from:

            query += """

                AND t.transaction_date >= %s

            """

            params.append(date_from)

        if date_to:

            query += """

                AND t.transaction_date <= %s

            """

            params.append(date_to)

        query += """

            ORDER BY

                t.transaction_date DESC,

                t.transaction_id DESC

        """

        cursor.execute(

            query,

            tuple(params)

        )

        expense_list = cursor.fetchall()

        filtered_total = sum(

            float(expense["amount"])

            for expense in expense_list

        )

        return render_template(

            "expenses.html",

            expenses=expense_list,

            categories=categories,

            search=search,

            selected_category=category_id,

            date_from=date_from,

            date_to=date_to,

            filtered_total=filtered_total

        )

    except Exception as error:

        print(

            "Expense history error:",

            error

        )

        flash(

            "Unable to load expenses.",

            "error"

        )

        return redirect(url_for("dashboard"))

    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()

# ==================================================

# EDIT EXPENSE

# ==================================================

@app.route(

    "/edit-expense/<int:transaction_id>",

    methods=["GET", "POST"]

)

def edit_expense(transaction_id):

    if "user_id" not in session:

        return redirect(url_for("login"))

    connection = None

    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor(

            dictionary=True

        )

        user_id = session["user_id"]

        cursor.execute(

            """

            SELECT

                t.transaction_id,

                t.amount,

                t.description,

                t.transaction_date,

                t.payment_method,

                t.category_id

            FROM transactions t

            JOIN categories c

                ON t.category_id = c.category_id

            WHERE t.transaction_id = %s

            AND t.user_id = %s

            AND c.type = 'expense'

            """,

            (

                transaction_id,

                user_id

            )

        )

        expense = cursor.fetchone()

        if not expense:

            flash(

                "Expense not found.",

                "error"

            )

            return redirect(url_for("expenses"))

        cursor.execute(

            """

            SELECT

                category_id,

                name

            FROM categories

            WHERE type = 'expense'

            AND (

                user_id IS NULL

                OR user_id = %s

            )

            ORDER BY name

            """,

            (user_id,)

        )

        categories = cursor.fetchall()

        if request.method == "POST":

            amount = request.form.get("amount")

            category_id = request.form.get(

                "category_id"

            )

            description = request.form.get(

                "description",

                ""

            ).strip()

            transaction_date = request.form.get(

                "transaction_date"

            )

            payment_method = request.form.get(

                "payment_method"

            )

            cursor.execute(

                """

                UPDATE transactions

                SET

                    category_id = %s,

                    amount = %s,

                    description = %s,

                    transaction_date = %s,

                    payment_method = %s

                WHERE transaction_id = %s

                AND user_id = %s

                """,

                (

                    category_id,

                    amount,

                    description,

                    transaction_date,

                    payment_method,

                    transaction_id,

                    user_id

                )

            )

            connection.commit()

            flash(

                "Expense updated successfully!",

                "success"

            )

            return redirect(url_for("expenses"))

        return render_template(

            "edit_expense.html",

            expense=expense,

            categories=categories

        )

    except Exception as error:

        print(

            "Edit expense error:",

            error

        )

        flash(

            "Unable to edit expense.",

            "error"

        )

        return redirect(url_for("expenses"))

    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()

# ==================================================

# DELETE EXPENSE

# ==================================================

@app.route(

    "/delete-expense/<int:transaction_id>",

    methods=["POST"]

)

def delete_expense(transaction_id):

    if "user_id" not in session:

        return redirect(url_for("login"))

    connection = None

    cursor = None

    try:

        connection = get_db_connection()

        cursor = connection.cursor()

        user_id = session["user_id"]

        cursor.execute(

            """

            DELETE FROM transactions

            WHERE transaction_id = %s

            AND user_id = %s

            """,

            (

                transaction_id,

                user_id

            )

        )

        connection.commit()

        if cursor.rowcount == 0:

            flash(

                "Expense not found.",

                "error"

            )

        else:

            flash(

                "Expense deleted successfully.",

                "success"

            )

        return redirect(url_for("expenses"))

    except Exception as error:

        print(

            "Delete expense error:",

            error

        )

        flash(

            "Unable to delete expense.",

            "error"

        )

        return redirect(url_for("expenses"))

    finally:

        if cursor:

            cursor.close()

        if connection:

            connection.close()

# ==================================================

# DATABASE TEST

# ==================================================

@app.route("/test-db")

def test_database():

    try:

        connection = get_db_connection()

        if connection.is_connected():

            connection.close()

            return "MySQL connection successful!"

        return "MySQL connection failed."

    except Exception as error:

        return f"Database error: {error}"

# ==================================================

# RUN

# ==================================================

if __name__ == "__main__":

    app.run(

        debug=True

    )
