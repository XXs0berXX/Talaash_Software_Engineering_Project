/**
 * Admin Claims Review Page
 * Shows pending claim requests and allows approval/rejection
 */

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/router';
import AuthGuard from '../../components/AuthGuard';
import { auth } from '../../lib/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import axios from 'axios';

function AdminClaimsContent() {
  const [loading, setLoading] = useState(true);
  const [claims, setClaims] = useState([]);
  const [token, setToken] = useState('');
  const [error, setError] = useState('');
  const [selectedClaim, setSelectedClaim] = useState(null);
  const [adminNotes, setAdminNotes] = useState('');
  const [processing, setProcessing] = useState(false);
  const router = useRouter();

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (user) => {
      if (user) {
        const userToken = await user.getIdToken();
        setToken(userToken);
        await fetchPendingClaims(userToken);
      }
    });

    return () => unsubscribe();
  }, []);

  const fetchPendingClaims = async (authToken) => {
    try {
      setLoading(true);
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/claims/pending`,
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
      setError('Failed to load claim requests');
    } finally {
      setLoading(false);
    }
  };

  const handleApproveClaim = async (claimId) => {
    if (!confirm('Approve this claim? The item will be marked as claimed and removed from the browse section.')) {
      return;
    }

    try {
      setProcessing(true);
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/claims/${claimId}/approve`,
        { admin_notes: adminNotes || 'Claim approved' },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.data.status === 'success') {
        alert('Claim approved successfully!');
        setSelectedClaim(null);
        setAdminNotes('');
        await fetchPendingClaims(token);
      }
    } catch (err) {
      console.error('Failed to approve claim:', err);
      alert('Failed to approve claim: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessing(false);
    }
  };

  const handleRejectClaim = async (claimId) => {
    const reason = prompt('Enter reason for rejection (will be sent to user):');
    if (!reason) return;

    try {
      setProcessing(true);
      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/admin/claims/${claimId}/reject`,
        { admin_notes: reason },
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );

      if (response.data.status === 'success') {
        alert('Claim rejected');
        setSelectedClaim(null);
        setAdminNotes('');
        await fetchPendingClaims(token);
      }
    } catch (err) {
      console.error('Failed to reject claim:', err);
      alert('Failed to reject claim: ' + (err.response?.data?.detail || err.message));
    } finally {
      setProcessing(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-12 max-w-7xl">
        <div className="flex justify-between items-center mb-8">
          <div>
            <button
              onClick={() => router.push('/admin/dashboard')}
              className="text-blue-600 hover:underline mb-2"
            >
              ← Back to Dashboard
            </button>
            <h1 className="text-4xl font-bold">Claim Requests</h1>
            <p className="text-gray-600 mt-2">Review and approve item claims</p>
          </div>
        </div>

        {/* Summary Banner */}
        {claims.length > 0 && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
            <div className="flex items-center">
              <span className="text-yellow-600 text-2xl mr-3">⏳</span>
              <div>
                <h3 className="font-bold text-yellow-800">
                  {claims.length} Pending Claim{claims.length !== 1 ? 's' : ''}
                </h3>
                <p className="text-sm text-yellow-700">
                  Review claims and verify ownership before approval
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Content */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            {loading ? (
              <div className="flex justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-blue-600 border-t-transparent"></div>
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-center">
                {error}
              </div>
            ) : claims.length === 0 ? (
              <div className="bg-gray-100 p-8 rounded-lg text-center">
                <p className="text-gray-600 text-lg">🎉 No pending claim requests!</p>
                <p className="text-sm text-gray-500 mt-2">
                  All claims have been processed
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {claims.map((claim) => (
                  <div
                    key={claim.claim_id}
                    className="border-2 border-gray-200 rounded-lg p-6 hover:border-blue-300 transition-colors"
                  >
                    <div className="flex gap-6">
                      {/* Item Image */}
                      {claim.item.image_url && (
                        <div className="flex-shrink-0">
                          <img
                            src={`${process.env.NEXT_PUBLIC_BACKEND_URL}${claim.item.image_url}`}
                            alt={claim.item.description}
                            className="w-40 h-40 object-cover rounded-lg border-2 border-gray-200"
                          />
                        </div>
                      )}

                      {/* Details */}
                      <div className="flex-1">
                        <div className="flex justify-between items-start mb-4">
                          <div>
                            <h3 className="text-xl font-bold text-gray-900 mb-2">
                              {claim.item.description}
                            </h3>
                            <div className="space-y-1 text-sm text-gray-600">
                              <p>📍 Found at: {claim.item.location}</p>
                              <p>📅 Date found: {new Date(claim.item.date_found).toLocaleDateString()}</p>
                            </div>
                          </div>
                          <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">
                            Pending Review
                          </span>
                        </div>

                        {/* Claimant Info */}
                        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
                          <h4 className="font-bold text-blue-900 mb-2">Claimant Information</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-sm">
                            <p><strong>Name:</strong> {claim.claimant.name}</p>
                            <p><strong>Email:</strong> {claim.claimant.email}</p>
                            <p><strong>Mobile:</strong> {claim.claimant.mobile}</p>
                            <p className="col-span-2">
                              <strong>Submitted:</strong> {new Date(claim.created_at).toLocaleString()}
                            </p>
                          </div>
                          {claim.claimant.notes && (
                            <div className="mt-3 pt-3 border-t border-blue-200">
                              <p className="font-semibold text-blue-900 mb-1">Claimant's Notes:</p>
                              <p className="text-gray-700 italic">"{claim.claimant.notes}"</p>
                            </div>
                          )}
                        </div>

                        {/* Admin Notes Input */}
                        {selectedClaim === claim.claim_id && (
                          <div className="mb-4">
                            <label className="block text-sm font-medium text-gray-700 mb-2">
                              Admin Notes (optional)
                            </label>
                            <textarea
                              value={adminNotes}
                              onChange={(e) => setAdminNotes(e.target.value)}
                              placeholder="Add any verification notes or comments..."
                              className="w-full border border-gray-300 rounded-lg p-3 text-sm"
                              rows="3"
                            />
                          </div>
                        )}

                        {/* Action Buttons */}
                        <div className="flex gap-3">
                          {selectedClaim === claim.claim_id ? (
                            <>
                              <button
                                onClick={() => handleApproveClaim(claim.claim_id)}
                                disabled={processing}
                                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-semibold disabled:opacity-50 transition-colors"
                              >
                                {processing ? 'Processing...' : '✓ Confirm Approval'}
                              </button>
                              <button
                                onClick={() => {
                                  setSelectedClaim(null);
                                  setAdminNotes('');
                                }}
                                disabled={processing}
                                className="bg-gray-300 hover:bg-gray-400 text-gray-800 px-6 py-2 rounded-lg font-semibold disabled:opacity-50 transition-colors"
                              >
                                Cancel
                              </button>
                            </>
                          ) : (
                            <>
                              <button
                                onClick={() => setSelectedClaim(claim.claim_id)}
                                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg font-semibold transition-colors"
                              >
                                ✓ Approve Claim
                              </button>
                              <button
                                onClick={() => handleRejectClaim(claim.claim_id)}
                                disabled={processing}
                                className="bg-red-600 hover:bg-red-700 text-white px-6 py-2 rounded-lg font-semibold disabled:opacity-50 transition-colors"
                              >
                                ✗ Reject Claim
                              </button>
                            </>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-blue-50 border border-blue-200 rounded-lg p-6">
          <h3 className="font-bold text-blue-900 mb-3">Review Guidelines</h3>
          <ul className="space-y-2 text-sm text-blue-800">
            <li>✓ Verify the claimant's identity and contact information</li>
            <li>✓ Check if the claimant can provide proof of ownership</li>
            <li>✓ Review any notes provided by the claimant</li>
            <li>✓ When approved, the item will be marked as claimed and removed from browse</li>
            <li>✓ All other pending claims for this item will be automatically rejected</li>
            <li>✓ Add admin notes for record-keeping purposes</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function AdminClaims() {
  return (
    <AuthGuard requiredRole="admin">
      <AdminClaimsContent />
    </AuthGuard>
  );
}