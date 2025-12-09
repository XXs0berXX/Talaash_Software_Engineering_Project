  /**
   * Admin Dashboard Page - WITH LOST ITEMS SUPPORT
   * Shows pending lost items that need approval
   */

  import React, { useState, useEffect } from 'react';
  import { useRouter } from 'next/router';
  import AuthGuard from '../../components/AuthGuard';
  import { auth } from '../../lib/firebase';
  import { onAuthStateChanged } from 'firebase/auth';
  import axios from 'axios';

  function AdminDashboardContent() {
    const [loading, setLoading] = useState(true);
    const [items, setItems] = useState([]);
    const [stats, setStats] = useState(null);
    const [token, setToken] = useState('');
    const [error, setError] = useState('');
    const [activeTab, setActiveTab] = useState('pending-lost'); // Show lost items by default
    const router = useRouter();

    useEffect(() => {
      const unsubscribe = onAuthStateChanged(auth, async (user) => {
        if (user) {
          const userToken = await user.getIdToken();
          setToken(userToken);
          await fetchDashboardData(userToken);
        }
      });

      return () => unsubscribe();
    }, []);

    useEffect(() => {
      if (token) {
        fetchItems(activeTab);
      }
    }, [activeTab, token]);

    const fetchDashboardData = async (authToken) => {
      try {
        setLoading(true);

        const dashResponse = await axios.get(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/dashboard`,
          {
            headers: {
              'Authorization': `Bearer ${authToken}`,
            },
          }
        );

        setStats(dashResponse.data.statistics);
        await fetchItems('pending-lost', authToken);
        setError('');
      } catch (err) {
        console.error('Failed to fetch dashboard data:', err);
        setError('Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    };

    const refreshStats = async () => {
      try {
        const dashResponse = await axios.get(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/dashboard`,
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );
        setStats(dashResponse.data.statistics);
      } catch (err) {
        console.error('Failed to refresh stats:', err);
      }
    };

    const fetchItems = async (status, authToken = token) => {
      try {
        setLoading(true);
        
        let endpoint = '';
        // LOST ITEMS
        if (status === 'pending-lost') {
          endpoint = '/api/admin/lost-items/pending';
        } 
        // FOUND ITEMS
        else if (status === 'approved') {
          endpoint = '/api/admin/items/approved';
        } else if (status === 'rejected') {
          endpoint = '/api/admin/items/rejected';
        } else {
          endpoint = '/api/admin/items/all';
        }

        const itemsResponse = await axios.get(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}${endpoint}`,
          {
            headers: {
              'Authorization': `Bearer ${authToken}`,
            },
            params: {
              limit: 50,
            },
          }
        );

        setItems(itemsResponse.data.items);
        setError('');
      } catch (err) {
        console.error('Failed to fetch items:', err);
        setError('Failed to load items');
      } finally {
        setLoading(false);
      }
    };

    // LOST ITEMS APPROVAL
    const handleApproveLost = async (itemId) => {
      try {
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/lost-items/${itemId}/approve`,
          {},
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        if (response.data.status === 'success') {
          setItems((prev) => prev.filter((item) => item.id !== itemId));
          await refreshStats();
          alert('Lost item approved!');
        }
      } catch (err) {
        console.error('Failed to approve lost item:', err);
        alert('Failed to approve lost item');
      }
    };

    const handleRejectLost = async (itemId) => {
      if (!confirm('Reject this lost item request?')) return;

      try {
        const response = await axios.post(
          `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/lost-items/${itemId}/reject`,
          {},
          {
            headers: {
              'Authorization': `Bearer ${token}`,
            },
          }
        );

        if (response.data.status === 'success') {
          setItems((prev) => prev.filter((item) => item.id !== itemId));
          await refreshStats();
        }
      } catch (err) {
        console.error('Failed to reject lost item:', err);
        alert('Failed to reject lost item');
      }
    };

    const getStatusBadge = (status) => {
      if (status === 'pending') {
        return <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">Pending</span>;
      } else if (status === 'approved') {
        return <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">Approved</span>;
      } else if (status === 'rejected') {
        return <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-semibold">Rejected</span>;
      }
      return null;
    };

    return (
      <div className="min-h-screen bg-gray-50">
        <div className="container mx-auto px-4 py-12 max-w-7xl">
          <div className="flex justify-between items-center mb-8">
            <h1 className="text-4xl font-bold">Admin Dashboard</h1>
            <button
              onClick={() => router.push('/admin/add-found-item')}
              className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 font-semibold"
            >
              + Add Found Item
            </button>
          </div>

          {/* Statistics */}
          {stats && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
              <div className="bg-white rounded-lg shadow p-6 text-center border-l-4 border-yellow-500">
                <h3 className="text-3xl font-bold text-yellow-600">
                  {stats.pending_lost_items || 0}
                </h3>
                <p className="text-gray-600 mt-2">Pending Lost Items</p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center border-l-4 border-green-500">
                <h3 className="text-3xl font-bold text-green-600">
                  {stats.approved_lost_items || 0}
                </h3>
                <p className="text-gray-600 mt-2">Approved Lost Items</p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center border-l-4 border-blue-500">
                <h3 className="text-3xl font-bold text-blue-600">
                  {stats.approved_items || 0}
                </h3>
                <p className="text-gray-600 mt-2">Found Items</p>
              </div>
              <div className="bg-white rounded-lg shadow p-6 text-center border-l-4 border-purple-500">
                <h3 className="text-3xl font-bold text-purple-600">
                  {(stats.total_items || 0) + (stats.total_lost_items || 0)}
                </h3>
                <p className="text-gray-600 mt-2">Total Items</p>
              </div>
            </div>
          )}

          {/* Tabs */}
          <div className="bg-white rounded-lg shadow">
            <div className="border-b border-gray-200">
              <div className="flex space-x-4 px-6">
                <button
                  onClick={() => setActiveTab('pending-lost')}
                  className={`py-4 px-4 border-b-2 font-semibold text-sm ${
                    activeTab === 'pending-lost'
                      ? 'border-yellow-600 text-yellow-600'
                      : 'border-transparent text-gray-500'
                  }`}
                >
                  Pending Lost ({stats?.pending_lost_items || 0})
                </button>
                <button
                  onClick={() => setActiveTab('approved')}
                  className={`py-4 px-4 border-b-2 font-semibold text-sm ${
                    activeTab === 'approved'
                      ? 'border-green-600 text-green-600'
                      : 'border-transparent text-gray-500'
                  }`}
                >
                  Found Items ({stats?.approved_items || 0})
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="p-6">
              {loading ? (
                <div className="flex justify-center py-12">
                  <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
                </div>
              ) : items.length === 0 ? (
                <div className="bg-gray-100 p-8 rounded-lg text-center">
                  <p className="text-gray-600">
                    {activeTab === 'pending-lost' ? '🎉 No pending lost items!' : 'No items'}
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  {items.map((item) => (
                    <div key={item.id} className="border rounded-lg p-4 flex gap-4">
                      {item.image_url && (
                        <img
                          src={`${process.env.NEXT_PUBLIC_BACKEND_URL}${item.image_url}`}
                          alt={item.description}
                          className="w-24 h-24 object-cover rounded"
                        />
                      )}

                      <div className="flex-1">
                        <h3 className="font-bold text-lg">{item.description}</h3>
                        <p className="text-sm text-gray-600">📍 {item.location}</p>
                        <p className="text-sm text-gray-600">
                          📅 {new Date(item.date_lost || item.created_at).toLocaleDateString()}
                        </p>
                      </div>

                      {activeTab === 'pending-lost' && (
                        <div className="flex gap-2 items-center">
                          <button
                            onClick={() => handleApproveLost(item.id)}
                            className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleRejectLost(item.id)}
                            className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    );
  }

  export default function AdminDashboard() {
    return (
      <AuthGuard requiredRole="admin">
        <AdminDashboardContent />
      </AuthGuard>
    );
  }