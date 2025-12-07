/**
 * My Claims Page
 * Shows user's submitted claim requests and their status
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import AuthGuard from '../components/AuthGuard';
import { auth } from '../lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import axios from 'axios';

function MyClaimsContent() {
  const [loading, setLoading] = useState(true);
  const [claims, setClaims] = useState([]);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        const userToken = await user.getIdToken();
        setToken(userToken);
        await fetchMyClaims(userToken);
      }
    });

    return () => unsubscribe();
  }, []);

  const fetchMyClaims = async (authToken) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/claims/my-claims`,
        {
          headers: {
            'Authorization': `Bearer ${authToken}`,
          },
        }
      );

      setClaims(response.data.claims || []);
      setError('');
    } catch (err) {
      console.error('Failed to fetch claims:', err);
      setError('Failed to load your claim requests');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    if (status === 'pending') {
      return (
        <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">
          ⏳ Pending Review
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
    }
    return null;
  };

  const getStatusMessage = (status, adminNotes) => {
    if (status === 'pending') {
      return (
        <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded p-3">
          <p className="text-sm text-yellow-800">
            ⏳ Your claim is being reviewed by an admin. You'll be notified once a decision is made.
          </p>
        </div>
      );
    } else if (status === 'approved') {
      return (
        <div className="mt-3 bg-green-50 border border-green-200 rounded p-3">
          <p className="text-sm text-green-800 font-semibold mb-1">
            ✅ Your claim has been approved!
          </p>
          <p className="text-sm text-green-700">
            Please visit the Lost & Found office to collect your item.
          </p>
          {adminNotes && (
            <p className="text-sm text-green-700 mt-2">
              <strong>Admin notes:</strong> {adminNotes}
            </p>
          )}
        </div>
      );
    } else if (status === 'rejected') {
      return (
        <div className="mt-3 bg-red-50 border border-red-200 rounded p-3">
          <p className="text-sm text-red-800 font-semibold mb-1">
            ❌ Your claim was not approved
          </p>
          {adminNotes && (
            <p className="text-sm text-red-700">
              <strong>Reason:</strong> {adminNotes}
            </p>
          )}
        </div>
      );
    }
    return null;
  };

  const pendingCount = claims.filter(c => c.status === 'pending').length;
  const approvedCount = claims.filter(c => c.status === 'approved').length;
  const rejectedCount = claims.filter(c => c.status === 'rejected').length;

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        <h1 className="text-4xl font-bold mb-8">My Claim Requests</h1>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-12">
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-blue-600">
              {claims.length}
            </h3>
            <p className="text-gray-600 mt-2">Total Claims</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-yellow-600">
              {pendingCount}
            </h3>
            <p className="text-gray-600 mt-2">Pending</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-green-600">
              {approvedCount}
            </h3>
            <p className="text-gray-600 mt-2">Approved</p>
          </div>
          <div className="bg-white rounded-lg shadow p-6 text-center">
            <h3 className="text-3xl font-bold text-red-600">
              {rejectedCount}
            </h3>
            <p className="text-gray-600 mt-2">Rejected</p>
          </div>
        </div>

        {/* Claims List */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            {loading ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-center">
                {error}
              </div>
            ) : claims.length === 0 ? (
              <div className="bg-gray-100 p-8 rounded-lg text-center">
                <p className="text-gray-600 mb-4">
                  You haven't submitted any claim requests yet
                </p>
                <button
                  onClick={() => router.push('/dashboard')}
                  className="bg-blue-600 text-white px-6 py-2 rounded hover:bg-blue-700 transition-colors"
                >
                  Browse Items
                </button>
              </div>
            ) : (
              <div className="space-y-6">
                {claims.map((claim) => (
                  <div
                    key={claim.claim_id}
                    className={`border-2 rounded-lg p-6 ${
                      claim.status === 'approved' ? 'border-green-300 bg-green-50' :
                      claim.status === 'rejected' ? 'border-red-300 bg-red-50' :
                      'border-gray-200'
                    }`}
                  >
                    <div className="flex gap-6">
                      {/* Item Image */}
                      {claim.item.image_url && (
                        <div className="flex-shrink-0">
                          <img
                            src={`${process.env.NEXT_PUBLIC_BACKEND_URL}${claim.item.image_url}`}
                            alt={claim.item.description}
                            className="w-32 h-32 object-cover rounded-lg border-2 border-gray-200"
                          />
                        </div>
                      )}

                      {/* Claim Details */}
                      <div className="flex-1">
                        <div className="flex items-start justify-between mb-3">
                          <div>
                            <h3 className="text-xl font-bold text-gray-900 mb-1">
                              {claim.item.description}
                            </h3>
                            <div className="space-y-1 text-sm text-gray-600">
                              <p>📍 {claim.item.location}</p>
                              <p>📅 Found: {new Date(claim.item.date_found).toLocaleDateString()}</p>
                              <p>🕐 Claimed: {new Date(claim.created_at).toLocaleString()}</p>
                            </div>
                          </div>
                          {getStatusBadge(claim.status)}
                        </div>

                        {/* Status Message */}
                        {getStatusMessage(claim.status, claim.admin_notes)}

                        {/* Item Status */}
                        {claim.item.status === 'claimed' && claim.status === 'approved' && (
                          <div className="mt-4 bg-blue-50 border border-blue-200 rounded p-3">
                            <p className="text-sm text-blue-800">
                              <strong>Item Status:</strong> This item has been marked as claimed. 
                              Please bring your ID to the Lost & Found office during office hours.
                            </p>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Information Box */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-bold text-blue-900 mb-3">About Claim Requests</h3>
          <ul className="space-y-2 text-sm text-blue-800">
            <li>✓ All claim requests are reviewed by administrators</li>
            <li>✓ Items remain visible to others until a claim is approved</li>
            <li>✓ You'll be notified once your claim is reviewed</li>
            <li>✓ Approved claims require you to visit the Lost & Found office</li>
            <li>✓ Bring valid ID and proof of ownership when collecting items</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function MyClaims() {
  return (
    <AuthGuard>
      <MyClaimsContent />
    </AuthGuard>
  );
}