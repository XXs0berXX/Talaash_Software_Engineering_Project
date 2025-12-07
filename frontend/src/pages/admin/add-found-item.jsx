/**
 * Admin Add Found Item Page
 * Form for admins to add items submitted to Lost & Found Office
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import FormInput from '../../components/FormInput';
import AuthGuard from '../../components/AuthGuard';
import { auth } from '../../lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import axios from 'axios';

function AdminAddFoundItemContent() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [token, setToken] = useState('');
  const [formData, setFormData] = useState({
    description: '',
    location: '',
    date_found: '',
    image: null,
  });
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        try {
          const userToken = await user.getIdToken();
          setToken(userToken);
        } catch (tokenError) {
          console.error("Failed to get Firebase ID Token:", tokenError);
          setError("Authentication failed: Could not get a valid user token.");
        }
      } else {
        setToken('');
      }
    });

    return () => unsubscribe();
  }, []);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files?.[0];
    if (file) {
      if (file.size > 5 * 1024 * 1024) {
        setError('File size must not exceed 5MB');
        return;
      }

      const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
      if (!allowedTypes.includes(file.type)) {
        setError('Only JPG, PNG, GIF, and WebP images are allowed');
        return;
      }

      setFormData((prev) => ({
        ...prev,
        image: file,
      }));
      setError('');
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // FIXED: Access form data from formData state object
    const { description, location, date_found, image } = formData;
    
    if (!description || !location || !date_found || !image) {
      setError('Please fill in all fields');
      return;
    }

    setLoading(true);
    setError('');

    try {
      const user = auth.currentUser;
      if (!user) {
        setError('Please sign in');
        return;
      }

      const userToken = await user.getIdToken();

      // Create FormData
      const submitData = new FormData();
      submitData.append('description', description);
      submitData.append('location', location);
      submitData.append('date_found', date_found);
      submitData.append('file', image);

      // Call admin endpoint
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/items/found/add`,
        submitData,
        {
          headers: {
            'Authorization': `Bearer ${userToken}`,
            'Content-Type': 'multipart/form-data',
          },
        }
      );

      if (response.data.status === 'success') {
        alert('✅ Found item added successfully and is now available for claiming!');
        router.push('/admin/dashboard');
      }
    } catch (err) {
      console.error('Failed to add found item:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to add found item';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        {/* Header */}
        <div className="mb-8">
          <button
            onClick={() => router.push('/admin/dashboard')}
            className="text-primary hover:underline mb-4"
          >
            ← Back to Dashboard
          </button>
          <h1 className="text-4xl font-bold mb-2">Add Found Item</h1>
          <p className="text-gray-600">
            Add items submitted to the Lost & Found Office
          </p>
        </div>

        <div className="flex justify-center">
          <div className="w-full max-w-2xl">
            <div className="bg-white rounded-lg shadow-md p-8">
              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg mb-4">
                  {error}
                </div>
              )}

              {success && (
                <div className="bg-green-50 border border-green-200 text-green-700 p-4 rounded-lg mb-4">
                  {success}
                </div>
              )}

              <form onSubmit={handleSubmit}>
                <FormInput
                  label="Item Description"
                  type="text"
                  placeholder="e.g., Blue backpack with laptop inside"
                  name="description"
                  value={formData.description}
                  onChange={handleChange}
                  required
                  disabled={loading}
                />

                <FormInput
                  label="Location Found"
                  type="text"
                  placeholder="e.g., Main Library 2nd Floor"
                  name="location"
                  value={formData.location}
                  onChange={handleChange}
                  required
                  disabled={loading}
                />

                <FormInput
                  label="Date & Time Found"
                  type="datetime-local"
                  name="date_found"
                  value={formData.date_found}
                  onChange={handleChange}
                  required
                  disabled={loading}
                />

                <div className="mb-4">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Item Image <span className="text-red-600">*</span>
                  </label>
                  <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center cursor-pointer hover:border-primary transition-colors">
                    <input
                      type="file"
                      id="image"
                      accept="image/*"
                      onChange={handleFileChange}
                      disabled={loading}
                      className="hidden"
                    />
                    <label htmlFor="image" className="cursor-pointer block">
                      {formData.image ? (
                        <div>
                          <p className="font-semibold text-primary">
                            {formData.image.name}
                          </p>
                          <p className="text-sm text-gray-600 mt-1">
                            Click to change image
                          </p>
                        </div>
                      ) : (
                        <div>
                          <p className="text-gray-600">Click to upload image</p>
                          <p className="text-sm text-gray-500 mt-1">
                            Max 5MB • JPG, PNG, GIF, WebP
                          </p>
                        </div>
                      )}
                    </label>
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-primary hover:bg-opacity-90 text-white font-bold py-3 rounded-lg transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {loading ? 'Adding Item...' : 'Add Found Item'}
                </button>
              </form>

              <div className="mt-6 pt-6 border-t">
                <h3 className="font-bold mb-2">Guidelines:</h3>
                <ul className="text-sm text-gray-600 space-y-2">
                  <li>✓ Provide a clear, detailed description</li>
                  <li>✓ Include distinguishing features or markings</li>
                  <li>✓ Upload a clear, well-lit image</li>
                  <li>✓ Specify the exact location where found</li>
                  <li>✓ Item will be immediately visible to all users once added</li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function AdminAddFoundItem() {
  return (
    <AuthGuard requiredRole="admin">
      <AdminAddFoundItemContent />
    </AuthGuard>
  );
}