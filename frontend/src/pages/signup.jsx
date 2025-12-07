/**
 * Signup Page
 * User registration with Firebase and backend validation
 * Now includes mobile number field
 */

import React, { useState } from "react";
import { useRouter } from "next/router";
import Link from "next/link";
import FormInput from "../components/FormInput";
import { auth } from "../lib/firebase";
import { createUserWithEmailAndPassword, updateProfile } from "firebase/auth";
import axios from "axios";

export default function Signup() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    mobile: "",
    password: "",
    confirmPassword: "",
  });
  const router = useRouter();

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const validateMobile = (mobile) => {
    // Remove spaces and dashes
    const cleaned = mobile.replace(/[\s\-\(\)]/g, '');
    
    // Check Pakistani mobile format
    const pattern1 = /^03[0-9]{9}$/; // 03XXXXXXXXX
    const pattern2 = /^\+923[0-9]{9}$/; // +923XXXXXXXXX
    
    return pattern1.test(cleaned) || pattern2.test(cleaned);
  };

  const validateForm = () => {
    if (!formData.name.trim()) {
      setError("Name is required");
      return false;
    }

    if (!formData.email.trim()) {
      setError("Email is required");
      return false;
    }

    // Fixed validation: Accept both @iba.edu.pk and @khi.iba.edu.pk
    const isValidIBAEmail = formData.email.endsWith("@iba.edu.pk") || 
                           formData.email.endsWith("@khi.iba.edu.pk");
    
    if (!isValidIBAEmail) {
      setError("Only @iba.edu.pk or @khi.iba.edu.pk email addresses are allowed");
      return false;
    }

    if (!formData.mobile.trim()) {
      setError("Mobile number is required");
      return false;
    }

    if (!validateMobile(formData.mobile)) {
      setError("Please enter a valid Pakistani mobile number (e.g., 03001234567)");
      return false;
    }

    if (!formData.password) {
      setError("Password is required");
      return false;
    }

    if (formData.password.length < 6) {
      setError("Password must be at least 6 characters");
      return false;
    }

    if (formData.password !== formData.confirmPassword) {
      setError("Passwords do not match");
      return false;
    }

    return true;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");

    if (!validateForm()) {
      return;
    }

    try {
      setLoading(true);

      // Step 1: Create user in Firebase
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        formData.email,
        formData.password
      );

      // Update display name
      await updateProfile(userCredential.user, {
        displayName: formData.name,
      });

      // Step 2: Create user record in backend
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/auth/signup`,
        {
          name: formData.name,
          email: formData.email,
          mobile: formData.mobile.replace(/[\s\-\(\)]/g, ''), // Clean mobile before sending
        }
      );

      if (response.status === 201) {
        // Success - redirect to login
        router.push("/login?signup=success");
      }
    } catch (err) {
      console.error("Signup failed:", err);
      
      if (err.code === "auth/email-already-in-use") {
        setError("Email already in use");
      } else if (err.response?.data?.detail) {
        const detail = err.response.data.detail;
        if (Array.isArray(detail) && detail.length > 0) {
          setError(detail[0].msg || "Validation failed");
        } else if (typeof detail === "string") {
          setError(detail);
        } else {
          setError("An unknown error occurred");
        }
      } else {
        setError(err.message || "Failed to create account");
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
            <h1 className="text-4xl font-bold text-gray-800 mb-2">Join Talash</h1>
            <p className="text-gray-600">Create your account to get started</p>
          </div>

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-6">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <FormInput
              label="Full Name"
              type="text"
              placeholder="John Doe"
              name="name"
              value={formData.name}
              onChange={handleChange}
              required
              disabled={loading}
            />

            <FormInput
              label="IBA Email"
              type="email"
              placeholder="john@khi.iba.edu.pk"
              name="email"
              value={formData.email}
              onChange={handleChange}
              required
              disabled={loading}
            />

            <FormInput
              label="Mobile Number"
              type="tel"
              placeholder="03001234567"
              name="mobile"
              value={formData.mobile}
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

            <FormInput
              label="Confirm Password"
              type="password"
              placeholder="••••••••"
              name="confirmPassword"
              value={formData.confirmPassword}
              onChange={handleChange}
              required
              disabled={loading}
            />

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-primary hover:bg-opacity-90 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? "Creating Account..." : "Sign Up"}
            </button>
          </form>

          <div className="mt-6 text-center">
            <p className="text-gray-600">
              Already have an account?{" "}
              <Link href="/login">
                <span className="text-primary font-bold cursor-pointer hover:underline">
                  Login here
                </span>
              </Link>
            </p>
          </div>

          <div className="mt-6 pt-6 border-t border-gray-200">
            <p className="text-sm text-gray-500 text-center">
              <strong>Note:</strong> Only @iba.edu.pk or @khi.iba.edu.pk email addresses are allowed
            </p>
          </div>

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