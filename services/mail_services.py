
from fastapi import BackgroundTasks
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from fastapi import BackgroundTasks
import asyncio

# ================= MAIL CONFIG =================

conf = ConnectionConfig(
    MAIL_USERNAME=SMTP_USER,
    MAIL_PASSWORD=SMTP_PASSWORD,
    MAIL_FROM=SMTP_USER,
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)

# ================= SEND EMAIL =================

async def send_html_email(
    to_email: str,
    subject: str,
    html_content: str
):
    try:

        message = MessageSchema(
            subject=subject,
            recipients=[to_email],
            body=html_content,
            subtype="html"
        )

        fm = FastMail(conf)

        await fm.send_message(message)

        print("Email sent successfully")

    except Exception as e:
        print(f"Failed to transmit email notification: {e}")

# ================= BACKGROUND TASK =================

def trigger_background_email(
    background_tasks: BackgroundTasks,
    to_email: str,
    subject: str,
    html_content: str
):
    """
    Queues email generation asynchronously
    to prevent API response delays.
    """

    background_tasks.add_task(
        send_html_email,
        to_email,
        subject,
        html_content
    )

# ================= EMAIL TEMPLATES =================

def get_welcome_template(name: str, email: str = "", profile_url: str = None) -> str:
    avatar_url = profile_url if profile_url else f"https://ui-avatars.com/api/?name={name}&background=00b118&color=fff"
    email_section = f'<p style="margin: 0 0 25px 0; color: #8e8e93; font-size: 14px;">{email}</p>' if email else ''
    app_url = os.getenv("APP_FRONTEND_URL", "http://localhost:5173")
    return f"""
    <html>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0e0e10; color: #f5f5f7; padding: 40px 20px; margin: 0;">
        <div style="
            max-width: 560px;
            margin: auto;
            background: #1c1c1e;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 8px 30px rgba(0, 0, 0, 0.5);
            border: 1px solid #2c2c2e;
        ">
            <!-- Header Banner with Green/Cyan Gradient -->
            <div style="
                background: linear-gradient(135deg, #00b118 0%, #31c9e7 100%);
                padding: 40px 30px;
                text-align: center;
            ">
                <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 800; letter-spacing: 1px;">MUSICO</h1>
                <p style="margin: 8px 0 0 0; color: #e2f9e4; font-size: 14px; font-weight: 500;">Lifetime Access Activated</p>
            </div>
            
            <!-- User Info Block -->
            <div style="padding: 30px 40px; text-align: center;">
                <div style="margin-bottom: 20px;">
                    <img src="{avatar_url}" 
                         alt="Profile" 
                         style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 3px solid #00b118; box-shadow: 0 4px 12px rgba(0, 177, 24, 0.3);" />
                </div>
                <h2 style="margin: 0 0 5px 0; color: #ffffff; font-size: 22px; font-weight: 700;">Welcome, {name}!</h2>
                {email_section}
                
                <div style="text-align: left; background: #2c2c2e; border-radius: 12px; padding: 20px 25px; margin-bottom: 30px;">
                    <h3 style="margin: 0 0 15px 0; color: #00b118; font-size: 16px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.5px;">Your Premium Features</h3>
                    
                    <table style="width: 100%; border-collapse: collapse;">
                        <tr>
                            <td style="padding: 8px 0; vertical-align: top; width: 30px; font-size: 18px;">✨</td>
                            <td style="padding: 8px 0; color: #e5e5ea; font-size: 14px; line-height: 1.4;">
                                <strong>Ad-Free High-Fidelity Audio</strong><br/>
                                Stream uninterrupted music at crystal clear 320kbps quality.
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; vertical-align: top; width: 30px; font-size: 18px;">📥</td>
                            <td style="padding: 8px 0; color: #e5e5ea; font-size: 14px; line-height: 1.4;">
                                <strong>High-Quality Downloads</strong><br/>
                                Keep your music offline and play them anywhere, anytime.
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; vertical-align: top; width: 30px; font-size: 18px;">🎧</td>
                            <td style="padding: 8px 0; color: #e5e5ea; font-size: 14px; line-height: 1.4;">
                                <strong>Private Room Listening</strong><br/>
                                Create private listening rooms to sync queues and play music with friends.
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 8px 0; vertical-align: top; width: 30px; font-size: 18px;">⚡</td>
                            <td style="padding: 8px 0; color: #e5e5ea; font-size: 14px; line-height: 1.4;">
                                <strong>Playlist & Queue Control</strong><br/>
                                Full management of your library with fast search, custom playlists, and advanced controls.
                            </td>
                        </tr>
                    </table>
                </div>

                <!-- CTA Button -->
                <div style="margin-top: 10px; margin-bottom: 10px;">
                    <a href="{app_url}/login" style="
                        display: inline-block;
                        background: linear-gradient(135deg, #00b118 0%, #31c9e7 100%);
                        color: #ffffff;
                        font-weight: 700;
                        font-size: 15px;
                        text-decoration: none;
                        padding: 14px 32px;
                        border-radius: 30px;
                        box-shadow: 0 4px 15px rgba(0, 177, 24, 0.4);
                    ">
                        Go to Dashboard
                    </a>
                </div>
            </div>

            <!-- Footer -->
            <div style="
                background: #121214;
                padding: 20px;
                text-align: center;
                border-top: 1px solid #2c2c2e;
            ">
                <p style="margin: 0; color: #636366; font-size: 12px;">© 2026 Musico India. All rights reserved.</p>
                <p style="margin: 5px 0 0 0; color: #636366; font-size: 11px;">You are receiving this because you registered for a premium account.</p>
            </div>
        </div>
    </body>
    </html>
    """

def get_otp_template(otp: str) -> str:
    return f"""
    <html>
    <body style="font-family: Arial; background:#f5f5f5; padding:20px;">

        <div style="
            max-width:600px;
            margin:auto;
            background:white;
            padding:30px;
            border-radius:12px;
            box-shadow:0 0 10px rgba(0,0,0,0.1);
        ">

            <h2 style="color:#1E90FF;">
                Password Reset Verification
            </h2>

            <p>
                Use the following OTP to reset your password:
            </p>

            <div style="
                font-size:36px;
                font-weight:bold;
                letter-spacing:8px;
                color:#6C5CE7;
                margin:20px 0;
            ">
                {otp}
            </div>

            <p>
                This OTP expires in <b>10 minutes</b>.
            </p>

            <hr>

            <p style="font-size:12px;color:gray;">
                If you did not request this,
                please ignore this email.
            </p>

        </div>

    </body>
    </html>
    """

def get_subscription_template(
    type_str: str,
    expiry
) -> str:

    return f"""
    <html>
    <body style="font-family: Arial; background:#f5f5f5; padding:20px;">

        <div style="
            max-width:600px;
            margin:auto;
            background:white;
            padding:30px;
            border-radius:12px;
            box-shadow:0 0 10px rgba(0,0,0,0.1);
        ">

            <h2 style="color:#00B894;">
                Premium Subscription Activated
            </h2>

            <p>
                Thank you for subscribing to Musico Premium.
            </p>

            <table style="
                width:100%;
                border-collapse:collapse;
                margin-top:20px;
            ">
                <tr>
                    <td style="padding:10px;"><b>Plan</b></td>
                    <td style="padding:10px;">{type_str}</td>
                </tr>

                <tr>
                    <td style="padding:10px;"><b>Expiry Date</b></td>
                    <td style="padding:10px;">
                        {expiry if expiry else "Lifetime"}
                    </td>
                </tr>
            </table>

            <p style="margin-top:20px;">
                Enjoy ad-free streaming,
                high-quality audio,
                unlimited skips,
                and premium features.
            </p>

            <hr>

            <p style="font-size:12px;color:gray;">
                Musico Premium Services
            </p>

        </div>

    </body>
    </html>
    """