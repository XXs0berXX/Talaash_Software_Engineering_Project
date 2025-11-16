/**
 * My Reports Page
 * Shows user's reported items with status filtering including rejected items
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import AuthGuard from '../components/AuthGuard';
import { auth } from '../lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import axios from 'axios';

function MyReportsContent() {
  const [loading, setLoading] = useState(true);
  const [foundItems, setFoundItems] = useState([]);
  const [lostItems, setLostItems] = useState([]);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('found'); // 'found' or 'lost'
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        const userToken = await user.getIdToken();
        setToken(userToken);
        await fetchMyReports(userToken);
      }
    });

    return () => unsubscribe();
  }, []);

  const fetchMyReports = async (authToken) => {
    try {
      setLoading(true);

      // Fetch found items
      const foundResponse = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/found/my-items`,
        {
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        }
      );

      // Fetch lost items
      const lostResponse = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/lost/my-items`,
        {
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        }
      );

      setFoundItems(foundResponse.data.items || []);
      setLostItems(lostResponse.data.items || []);
      setError('');
    } catch (err) {
      console.error('Failed to fetch reports:', err);
      setError('Failed to load your reports');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    if (status === 'pending') {
      return (
        <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">
          ⏳ Pending Approval
        </span>
      );
    } else if (status === 'approved') {
      return (
        <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
          ✅ Approved
        </span>
      );
    } else if (status === 'rejected') {
      return (
        <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-semibold">
          ❌ Rejected
        </span>
      );
    } else if (status === 'claimed') {
      return (
        <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold">
          🎉 Claimed
        </span>
      );
    }
    return null;
  };

  const currentItems = activeTab === 'found' ? foundItems : lostItems;
  const pendingCount = currentItems.filter(item => item.status === 'pending').length;
  const approvedCount = currentItems.filter(item => item.status === 'approved').length;
  const rejectedCount = currentItems.filter(item => item.status === 'rejected').length;

  const handleDeleteItem = async (itemId, type) => {
    if (!confirm('Are you sure you want to delete this report?')) {
      return;
    }

    try {
      const user = auth.currentUser;
      if (!user) {
        alert('Please log in to delete items');
        return;
      }

      const userToken = await user.getIdToken();

      await axios.delete(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/${type}/${itemId}`,
        {
          headers: {
            'Authorization': `Bearer ${userToken}`,
          },
        }
      );

      // Refresh the list
      await fetchMyReports(userToken);
      alert('Item deleted successfully');
    } catch (err) {
      console.error('Delete failed:', err);
      alert('Failed to delete item. Please try again.');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        <h1 className="text-4xl font-bold mb-8">My Reports</h1>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-blue-600">
              {foundItems.length}
            </h3>
            <p className="text-gray-600 mt-2">Found Items</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-purple-600">
              {lostItems.length}
            </h3>
            <p className="text-gray-600 mt-2">Lost Items</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-green-600">
              {approvedCount}
            </h3>
            <p className="text-gray-600 mt-2">Approved</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-yellow-600">
              {pendingCount}
            </h3>
            <p className="text-gray-600 mt-2">Pending</p>
          </div>
        </div>

        {/* Status Info Banner */}
        {rejectedCount > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <div className="flex items-start">
              <span className="text-red-600 text-xl mr-3">⚠️</span>
              <div>
                <h3 className="font-bold text-red-800 mb-1">
                  You have {rejectedCount} rejected {rejectedCount === 1 ? 'item' : 'items'}
                </h3>
                <p className="text-sm text-red-700">
                  These items did not meet our guidelines. Please review and resubmit with correct information.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Tabs */}
        <div className="bg-white rounded-lg shadow">
          {/* Tab Headers */}
          <div className="border-b border-gray-200">
            <div className="flex space-x-8 px-6">
              <button
                onClick={() => setActiveTab('found')}
                className={`py-4 px-2 border-b-2 font-semibold text-sm transition-colors ${
                  activeTab === 'found'
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Found Items ({foundItems.length})
              </button>
              <button
                onClick={() => setActiveTab('lost')}
                className={`py-4 px-2 border-b-2 font-semibold text-sm transition-colors ${
                  activeTab === 'lost'
                    ? 'border-purple-600 text-purple-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                Lost Items ({lostItems.length})
              </button>
            </div>
          </div>

          {/* Tab Content */}
          <div className="p-6">
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-center">
                {error}
              </div>
            ) : currentItems.length === 0 ? (
              <div className="bg-gray-100 p-8 rounded-lg text-center">
                <p className="text-gray-600 mb-4">
                  You haven't reported any {activeTab} items yet
                </p>
                <button
                  onClick={() => router.push(`/report-${activeTab}`)}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition-colors"
                >
                  Report {activeTab === 'found' ? 'Found' : 'Lost'} Item
                </button>
              </div>
            ) : (
              <div className="space-y-4">
                {currentItems.map((item) => (
                  <div
                    key={item.id}
                    className={`border rounded-lg p-4 flex gap-4 hover:shadow-md transition-shadow ${
                      item.status === 'rejected' ? 'border-red-300 bg-red-50' : 'border-gray-200'
                    }`}
                  >
                    {/* Item Image */}
                    {item.image_url && (
                      <img
                        src={`${process.env.NEXT_PUBLIC_BACKEND_URL}${item.image_url}`}
                        alt={item.description}
                        className="w-24 h-24 object-cover rounded"
                      />
                    )}

                    {/* Item Details */}
                    <div className="flex-1">
                      <div className="flex items-start justify-between mb-2">
                        <h3 className="font-bold text-lg">
                          {item.description}
                        </h3>
                        {getStatusBadge(item.status)}
                      </div>
                      <p className="text-sm text-gray-600 mb-1">
                        📍 {item.location}
                      </p>
                      <p className="text-sm text-gray-600">
                        📅 {new Date(item.date_found || item.date_lost || item.created_at).toLocaleDateString()}
                      </p>
                      {item.category && (
                        <p className="text-sm text-gray-600 mt-1">
                          🏷️ {item.category}
                        </p>
                      )}
                      
                      {/* Status-specific messages */}
                      {item.status === 'pending' && (
                        <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded p-2">
                          <p className="text-sm text-yellow-800">
                            ⏳ Your item is awaiting admin approval. You'll be notified once it's reviewed.
                          </p>
                        </div>
                      )}
                      
                      {item.status === 'rejected' && (
                        <div className="mt-3 bg-red-50 border border-red-200 rounded p-2">
                          <p className="text-sm text-red-800 font-semibold mb-1">
                            ❌ This item was rejected
                          </p>
                          <p className="text-sm text-red-700">
                            Please ensure your submission follows our guidelines and resubmit with accurate information.
                          </p>
                        </div>
                      )}
                      
                      {item.status === 'approved' && (
                        <div className="mt-3 bg-green-50 border border-green-200 rounded p-2">
                          <p className="text-sm text-green-800">
                            ✅ Your item is now visible to all users
                          </p>
                        </div>
                      )}
                    </div>

                    {/* Delete Button */}
                    <div className="flex items-start">
                      <button
                        onClick={() => handleDeleteItem(item.id, activeTab)}
                        className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded text-sm font-semibold transition-colors"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="mt-8 bg-white rounded-lg shadow p-6">
          <h3 className="text-xl font-bold mb-4">Quick Actions</h3>
          <div className="max-w-md">
            <button
              onClick={() => router.push('/report-found')}
              className="bg-primary hover:bg-opacity-90 text-white font-semibold py-3 px-6 rounded-lg transition-colors"
            >
              Report Lost Item
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function MyReports() {
  return (
    <AuthGuard>
      <MyReportsContent />
    </AuthGuard>
  );
}