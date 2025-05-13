from app import app, db, User
from werkzeug.security import generate_password_hash

with app.app_context():
    if not User.query.filter_by(username='admin').first():
        admin_user = User(
            username='admin',
            email='admin@admin.com',
            first_name='Admin',
            password=generate_password_hash('Admin123!', method='pbkdf2:sha256'),
            is_admin=True
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Admin user created.")
    else:
        print("ℹ️ Admin user already exists.")
