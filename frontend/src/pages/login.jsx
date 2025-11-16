/**
 * Login Page
 * User login with Firebase and backend token validation
 */

import React, { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import FormInput from "../components/FormInput";
import { auth } from "../lib/firebase";
import {
  signInWithEmailAndPassword,
  sendPasswordResetEmail,
} from "firebase/auth";
import axios from "axios";

export default function Login() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [resetEmail, setResetEmail] = useState("");
  const [formData, setFormData] = useState({
    email: "",
    password: "",
  });
  const router = useRouter();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!formData.email || !formData.password) {
      setError("Please fill in all fields");
      return;
    }

    try {
      setLoading(true);

      // Step 1: Authenticate with Firebase
      const userCredential = await signInWithEmailAndPassword(
        auth,
        formData.email,
        formData.password
      );

      // Get Firebase token
      const token = await userCredential.user.getIdToken();

      console.log(
        "Firebase ID Token Generated:",
        token.substring(0, 30) + "..."
      );

      // Step 2: Validate token with backend
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/auth/login`,
        {
          email: formData.email,
          token: token,
        }
      );

      if (response.data.status === "success") {
        // Check if user is admin - block admin login through user portal
        if (response.data.user.role === "admin") {
          await auth.signOut(); // Sign out from Firebase
          setError(
            "Admin accounts cannot login here. Please use the admin login page."
          );
          return;
        }

        // Store token in localStorage for future requests
        localStorage.setItem("authToken", token);
        localStorage.setItem("user", JSON.stringify(response.data.user));

        // Redirect to user dashboard
        window.location.replace("/admin/dashboard");
      }
    } catch (err) {
      console.error("Login failed:", err);

      if (err.code === "auth/user-not-found") {
        setError("No account found with this email");
      } else if (err.code === "auth/wrong-password") {
        setError("Incorrect password");
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (Array.isArray(detail) && detail.length > 0) {
          setError(detail[0].msg || "Validation failed");
        } else if (typeof detail === "string") {
          setError(detail);
        } else {
          setError("An unknown backend error occurred.");
        }
      } else {
        setError(err.message || "Failed to login");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (!resetEmail) {
      setError("Please enter your email address");
      return;
    }

    // Only accept @khi.iba.edu.pk
    if (!resetEmail.endsWith("@khi.iba.edu.pk")) {
      setError("Please use your IBA Karachi email address (@khi.iba.edu.pk)");
      return;
    }

    try {
      setLoading(true);

      await sendPasswordResetEmail(auth, resetEmail);

      setSuccess("Password reset email sent! Check your inbox.");
      setResetEmail("");

      // Close the forgot password modal after 3 seconds
      setTimeout(() => {
        setShowForgotPassword(false);
        setSuccess("");
      }, 3000);
    } catch (err) {
      console.error("Password reset failed:", err);

      if (err.code === "auth/user-not-found") {
        setError("No account found with this email");
      } else if (err.code === "auth/invalid-email") {
        setError("Invalid email address");
      } else {
        setError(err.message || "Failed to send reset email");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-primary to-secondary flex items-center justify-center py-12 px-4">
      <div className="w-full max-w-md">
        <div className="bg-white rounded-2xl shadow-2xl p-8">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-2">
              {showForgotPassword ? "Reset Password" : "Welcome Back"}
            </h1>
            <p className="text-gray-600">
              {showForgotPassword
                ? "Enter your email to receive a reset link"
                : "Login to your Talash account"}
            </p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-6">
              {error}
            </div>
          )}

          {success && (
            <div className="bg-green-50 border border-green-200 text-green-700 p-4 rounded-lg mb-6">
              {success}
            </div>
          )}

          {/* Forgot Password Form */}
          {showForgotPassword ? (
            <form onSubmit={handleForgotPassword} className="space-y-4">
              <FormInput
                label="IBA Email"
                type="email"
                placeholder="your@khi.iba.edu.pk"
                name="resetEmail"
                value={resetEmail}
                onChange={(e) => setResetEmail(e.target.value)}
                required
                disabled={loading}
              />

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary hover:bg-opacity-90 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Sending..." : "Send Reset Link"}
              </button>

              <button
                type="button"
                onClick={() => {
                  setShowForgotPassword(false);
                  setError("");
                  setSuccess("");
                }}
                className="w-full text-gray-600 hover:text-primary font-semibold py-2"
              >
                ← Back to Login
              </button>
            </form>
          ) : (
            // Login Form
            <form onSubmit={handleSubmit} className="space-y-4">
              <FormInput
                label="IBA Email"
                type="email"
                placeholder="your@khi.iba.edu.pk"
                name="email"
                value={formData.email}
                onChange={handleChange}
                required
                disabled={loading}
              />

              <FormInput
                label="Password"
                type="password"
                placeholder="••••••••"
                name="password"
                value={formData.password}
                onChange={handleChange}
                required
                disabled={loading}
              />

              {/* Forgot Password Link */}
              <div className="text-right">
                <button
                  type="button"
                  onClick={() => setShowForgotPassword(true)}
                  className="text-sm text-primary hover:underline font-semibold"
                >
                  Forgot Password?
                </button>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary hover:bg-opacity-90 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {loading ? "Logging in..." : "Login"}
              </button>
            </form>
          )}

          {!showForgotPassword && (
            <>
              <div className="mt-6 text-center">
                <p className="text-gray-600">
                  Don't have an account?{" "}
                  <Link href="/signup">
                    <span className="text-primary font-bold cursor-pointer hover:underline">
                      Sign up here
                    </span>
                  </Link>
                </p>
              </div>

              <div className="mt-6 pt-6 border-t border-gray-200 text-center">
                <Link href="/admin/login">
                  <span className="text-sm text-gray-500 hover:text-primary cursor-pointer">
                    Admin Login →
                  </span>
                </Link>
              </div>
            </>
          )}

          {/* Back to Home Link */}
          <div className="mt-4 text-center">
            <Link href="/">
              <span className="text-sm text-gray-500 hover:text-primary cursor-pointer">
                ← Back to Home
              </span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
