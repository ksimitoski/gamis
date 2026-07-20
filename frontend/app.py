import os
import requests
from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "gamis-secret-key-12345")
BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")

@app.context_processor
def inject_banner():
    if "BANNER_TEXT" not in app.config:
        try:
            res = requests.get(f"{BACKEND_URL}/api/config/banner", timeout=2)
            if res.status_code == 200:
                app.config["BANNER_TEXT"] = res.json().get("value", "gamis")
            else:
                app.config["BANNER_TEXT"] = "gamis"
        except Exception:
            app.config["BANNER_TEXT"] = "gamis"
    return {"banner_text": app.config.get("BANNER_TEXT", "gamis")}

# -----------------

# Helpers
# -----------------
def get_auth_headers():
    token = session.get("token")
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}

def check_login():
    if "token" not in session:
        return False
    return True

# -----------------
# Auth Routes
# -----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        try:
            # Login against backend
            res = requests.post(
                f"{BACKEND_URL}/api/auth/login",
                json={"username": username, "password": password}
            )
            if res.status_code == 200:
                token_data = res.json()
                session["token"] = token_data["access_token"]
                session["username"] = username
                
                # Fetch user details to see if admin
                user_headers = {"Authorization": f"Bearer {token_data['access_token']}"}
                # Check if the user is an admin by attempting to query the list of users (only allowed for admins)
                users_res = requests.get(f"{BACKEND_URL}/api/users", headers=user_headers)
                if users_res.status_code == 200:
                    session["is_admin"] = True
                else:
                    session["is_admin"] = False

                flash("Welcome back!", "success")
                return redirect(url_for("index"))
            else:
                flash("Invalid username or password.", "danger")
        except Exception as e:
            flash(f"Backend offline: {str(e)}", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    if not check_login():
        return redirect(url_for("login"))

    if request.method == "POST":
        current_password = request.form.get("current_password")
        new_password = request.form.get("new_password")

        try:
            res = requests.put(
                f"{BACKEND_URL}/api/users/me/password",
                json={
                    "current_password": current_password,
                    "new_password": new_password
                },
                headers=get_auth_headers()
            )
            if res.status_code == 200:
                flash("Your password has been changed successfully!", "success")
                return redirect(url_for("index"))
            else:
                try:
                    err_msg = res.json().get("detail", "Password change failed.")
                except Exception:
                    err_msg = "Unknown backend error."
                flash(f"Error: {err_msg}", "danger")
        except Exception as e:
            flash(f"Backend offline: {str(e)}", "danger")

    return render_template("change_password.html")

@app.route("/admin", methods=["GET", "POST"])
def admin_dashboard():
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_admin"):
        flash("Access denied: Administrator privileges required.", "danger")
        return redirect(url_for("index"))

    current_banner = app.config.get("BANNER_TEXT", "gamis")

    if request.method == "POST":
        new_banner = request.form.get("banner_text", "").strip()
        if not new_banner:
            flash("Banner text cannot be empty.", "warning")
        else:
            try:
                res = requests.post(
                    f"{BACKEND_URL}/api/config/banner",
                    json={"value": new_banner},
                    headers=get_auth_headers()
                )
                if res.status_code == 200:
                    app.config["BANNER_TEXT"] = new_banner
                    current_banner = new_banner
                    flash("Banner text updated successfully!", "success")
                else:
                    flash("Failed to update banner text.", "danger")
            except Exception as e:
                flash(f"Error communicating with backend: {str(e)}", "danger")

    return render_template("admin.html", current_banner=current_banner)

@app.route("/users")
def list_users():
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_admin"):
        flash("Access denied: Administrator privileges required.", "danger")
        return redirect(url_for("index"))

    try:
        res = requests.get(f"{BACKEND_URL}/api/users", headers=get_auth_headers())
        if res.status_code == 200:
            users = res.json()
        else:
            users = []
            flash("Failed to retrieve users.", "warning")
    except Exception as e:
        users = []
        flash(f"Backend service is unreachable: {str(e)}", "danger")

    return render_template("users.html", users=users)

@app.route("/users/add", methods=["GET", "POST"])
def create_user():
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_admin"):
        flash("Access denied: Administrator privileges required.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        is_admin = True if request.form.get("is_admin") else False

        try:
            res = requests.post(
                f"{BACKEND_URL}/api/users",
                json={"username": username, "password": password, "is_admin": is_admin},
                headers=get_auth_headers()
            )
            if res.status_code == 201:
                flash(f"User '{username}' registered successfully!", "success")
                return redirect(url_for("list_users"))
            else:
                try:
                    err_msg = res.json().get("detail", "Registration failed.")
                except Exception:
                    err_msg = "Unknown backend error."
                flash(f"Error: {err_msg}", "danger")
        except Exception as e:
            flash(f"Backend offline: {str(e)}", "danger")

    return render_template("create_user.html")

@app.route("/users/edit/<user_id>", methods=["GET", "POST"])
def edit_user(user_id):
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_admin"):
        flash("Access denied: Administrator privileges required.", "danger")
        return redirect(url_for("index"))

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password") or None
        is_admin = True if request.form.get("is_admin") else False

        payload = {"username": username, "is_admin": is_admin}
        if password:
            payload["password"] = password

        try:
            res = requests.put(
                f"{BACKEND_URL}/api/users/{user_id}",
                json=payload,
                headers=get_auth_headers()
            )
            if res.status_code == 200:
                flash(f"User '{username}' updated successfully!", "success")
                return redirect(url_for("list_users"))
            else:
                try:
                    err_msg = res.json().get("detail", "Update failed.")
                except Exception:
                    err_msg = "Unknown backend error."
                flash(f"Error: {err_msg}", "danger")
        except Exception as e:
            flash(f"Backend offline: {str(e)}", "danger")

    # GET request
    try:
        res = requests.get(f"{BACKEND_URL}/api/users", headers=get_auth_headers())
        if res.status_code == 200:
            users = res.json()
            user = next((u for u in users if u["id"] == user_id), None)
            if not user:
                flash("User not found.", "danger")
                return redirect(url_for("list_users"))
            return render_template("user_edit.html", user=user)
        else:
            flash("Failed to retrieve users details.", "danger")
            return redirect(url_for("list_users"))
    except Exception as e:
        flash(f"Error connecting to backend: {str(e)}", "danger")
        return redirect(url_for("list_users"))

@app.route("/users/delete/<user_id>", methods=["POST"])
def delete_user(user_id):
    if not check_login():
        return redirect(url_for("login"))
    if not session.get("is_admin"):
        flash("Access denied: Administrator privileges required.", "danger")
        return redirect(url_for("index"))

    try:
        res = requests.delete(f"{BACKEND_URL}/api/users/{user_id}", headers=get_auth_headers())
        if res.status_code == 204:
            flash("User deleted successfully!", "success")
        else:
            try:
                err_msg = res.json().get("detail", "Failed to delete user.")
            except Exception:
                err_msg = "Failed to delete user."
            flash(f"Error: {err_msg}", "danger")
    except Exception as e:
        flash(f"Error connecting to backend: {str(e)}", "danger")
    return redirect(url_for("list_users"))

# -----------------
# Inventory Routes
# -----------------
@app.route("/")
def index():
    if not check_login():
        return redirect(url_for("login"))

    try:
        res = requests.get(f"{BACKEND_URL}/api/items", headers=get_auth_headers())
        if res.status_code == 401:
            session.clear()
            return redirect(url_for("login"))
        elif res.status_code == 200:
            items = res.json()
        else:
            items = []
            flash("Failed to retrieve inventory items.", "warning")
    except Exception as e:
        items = []
        flash(f"Backend service is unreachable: {str(e)}", "danger")

    # Compute dashboard statistics
    total_items = len(items)
    total_cost = sum(item.get("cost", 0.0) for item in items)
    total_value = sum(item.get("price", 0.0) for item in items)
    potential_profit = total_value - total_cost

    return render_template(
        "index.html",
        items=items,
        total_items=total_items,
        total_cost=total_cost,
        total_value=total_value,
        potential_profit=potential_profit
    )

@app.route("/uploads/<filename>")
def get_upload(filename):
    if not check_login():
        return "Unauthorized", 401
    try:
        res = requests.get(f"{BACKEND_URL}/uploads/{filename}", headers=get_auth_headers(), stream=True)
        if res.status_code == 200:
            from flask import Response
            return Response(res.raw, content_type=res.headers.get("content-type"))
    except Exception:
        pass
    return "Not Found", 404

@app.route("/item/<item_id>")
def item_detail(item_id):
    if not check_login():
        return redirect(url_for("login"))
    try:
        res = requests.get(f"{BACKEND_URL}/api/items/{item_id}", headers=get_auth_headers())
        if res.status_code == 401:
            session.clear()
            return redirect(url_for("login"))
        elif res.status_code == 200:
            item = res.json()
            return render_template("item_detail.html", item=item)
        else:
            flash("Item not found.", "danger")
            return redirect(url_for("index"))
    except Exception as e:
        flash(f"Error connecting to database service: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/add", methods=["GET", "POST"])
def add_item():
    if not check_login():
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name")
        date = request.form.get("date")
        item_type = request.form.get("type")
        weight = request.form.get("weight")
        cost = request.form.get("cost")
        price = request.form.get("price")
        custom_id = request.form.get("custom_id")
        photo = request.files.get("photo")

        data = {
            "name": name,
            "date": date,
            "type": item_type,
            "weight": weight,
            "cost": cost,
            "price": price,
            "custom_id": custom_id
        }
        files = None
        if photo and photo.filename:
            files = {"photo": (photo.filename, photo.read(), photo.content_type)}

        try:
            res = requests.post(
                f"{BACKEND_URL}/api/items",
                data=data,
                files=files,
                headers=get_auth_headers()
            )
            if res.status_code == 201:
                flash("Inventory item added successfully!", "success")
                return redirect(url_for("index"))
            else:
                try:
                    err_msg = res.json().get("detail", "Validation failed.")
                except Exception:
                    err_msg = "Unknown backend error."
                flash(f"Error creating item: {err_msg}", "danger")
        except Exception as e:
            flash(f"Failed to transmit data to backend service: {str(e)}", "danger")

    return render_template("item_form.html", action="Add", item=None)

@app.route("/edit/<item_id>", methods=["GET", "POST"])
def edit_item(item_id):
    if not check_login():
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("name")
        date = request.form.get("date")
        item_type = request.form.get("type")
        weight = request.form.get("weight")
        cost = request.form.get("cost")
        price = request.form.get("price")
        custom_id = request.form.get("custom_id")
        photo = request.files.get("photo")

        data = {
            "name": name,
            "date": date,
            "type": item_type,
            "weight": weight,
            "cost": cost,
            "price": price,
            "custom_id": custom_id
        }
        files = None
        if photo and photo.filename:
            files = {"photo": (photo.filename, photo.read(), photo.content_type)}

        try:
            res = requests.put(
                f"{BACKEND_URL}/api/items/{item_id}",
                data=data,
                files=files,
                headers=get_auth_headers()
            )
            if res.status_code == 200:
                flash("Inventory item updated successfully!", "success")
                return redirect(url_for("item_detail", item_id=item_id))
            else:
                try:
                    err_msg = res.json().get("detail", "Validation failed.")
                except Exception:
                    err_msg = "Unknown backend error."
                flash(f"Error updating item: {err_msg}", "danger")
        except Exception as e:
            flash(f"Failed to transmit data to backend service: {str(e)}", "danger")

    # GET request
    try:
        res = requests.get(f"{BACKEND_URL}/api/items/{item_id}", headers=get_auth_headers())
        if res.status_code == 200:
            item = res.json()
            return render_template("item_form.html", action="Edit", item=item)
        else:
            flash("Item not found.", "danger")
            return redirect(url_for("index"))
    except Exception as e:
        flash(f"Error connecting to backend: {str(e)}", "danger")
        return redirect(url_for("index"))

@app.route("/delete/<item_id>", methods=["POST"])
def delete_item(item_id):
    if not check_login():
        return redirect(url_for("login"))
    try:
        res = requests.delete(f"{BACKEND_URL}/api/items/{item_id}", headers=get_auth_headers())
        if res.status_code == 204:
            flash("Item deleted successfully!", "success")
        else:
            flash("Failed to delete item from database.", "danger")
    except Exception as e:
        flash(f"Error connecting to backend: {str(e)}", "danger")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
