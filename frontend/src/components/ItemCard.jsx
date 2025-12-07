/**
 * ItemCard Component
 * Displays found or lost item details in a card format
 * Includes claim functionality with modal
 */

import React, { useState } from 'react';
import axios from 'axios';
import { auth } from '../lib/firebase';

export default function ItemCard({
  item,
  type = 'found', // 'found' or 'lost'
  onClaimClick,
  showClaimButton = true,
}) {
  const [showClaimModal, setShowClaimModal] = useState(false);
  const [claimData, setClaimData] = useState({
    name: '',
    email: '',
    mobile: '',
    notes: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const statusColors = {
    pending: 'bg-warning',
    approved: 'bg-success',
    claimed: 'bg-primary',
    found: 'bg-success',
  };

  const dateField = type === 'found' ? 'date_found' : 'date_lost';
  const itemDate = new Date(item[dateField]);

  const handleClaimClick = () => {
    // If parent provided a custom handler, use it
    if (onClaimClick) {
      onClaimClick(item.id);
      return;
    }
    
    // Otherwise, show our modal
    setShowClaimModal(true);
    setError(null);
  };

  const handleClaimSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const user = auth.currentUser;
      if (!user) {
        throw new Error('You must be logged in to claim items');
      }

      const token = await user.getIdToken();

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/found/${item.id}/claim`,
        claimData,
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );

      // Success!
      alert(response.data.message || 'Claim submitted successfully!');
      setShowClaimModal(false);
      
      // Reload the page to show updated status
      window.location.reload();
    } catch (err) {
      console.error('Claim error:', err);
      setError(
        err.response?.data?.detail || 
        err.message || 
        'Failed to submit claim. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  const handleInputChange = (e) => {
    setClaimData({
      ...claimData,
      [e.target.name]: e.target.value
    });
  };

  return (
    <>
      <div className="card w-full">
        {/* Image */}
        {item.image_url && (
          <img
            src={`${process.env.NEXT_PUBLIC_BACKEND_URL}${item.image_url}`}
            alt={item.description}
            className="w-full h-48 object-cover rounded-lg mb-4"
          />
        )}

        {/* Header */}
        <div className="flex justify-between items-start mb-3">
          <h3 className="text-lg font-bold text-dark line-clamp-2">
            {item.description}
          </h3>
          <span
            className={`${statusColors[item.status] || 'bg-gray-400'} text-white text-xs px-3 py-1 rounded-full`}
          >
            {item.status}
          </span>
        </div>

        {/* Location */}
        <div className="mb-2">
          <p className="text-sm text-gray-600">
            <strong>📍 Location:</strong> {item.location}
          </p>
        </div>

        {/* Date */}
        <div className="mb-3">
          <p className="text-sm text-gray-600">
            <strong>📅 {type === 'found' ? 'Found' : 'Lost'}:</strong>{' '}
            {itemDate.toLocaleDateString()} {itemDate.toLocaleTimeString()}
          </p>
        </div>

        {/* Description */}
        <div className="mb-4">
          <p className="text-gray-700 text-sm line-clamp-3">
            {item.description}
          </p>
        </div>

        {/* Actions */}
        {showClaimButton && item.status === 'approved' && (
          <button
            onClick={handleClaimClick}
            className="btn-primary w-full"
          >
            {type === 'found' ? 'Claim Item' : 'Report Found'}
          </button>
        )}
      </div>

      {/* Claim Modal */}
      {showClaimModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-2xl font-bold">Claim This Item</h2>
              <button
                onClick={() => setShowClaimModal(false)}
                className="text-gray-500 hover:text-gray-700 text-2xl"
              >
                ×
              </button>
            </div>

            {error && (
              <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded mb-4">
                {error}
              </div>
            )}

            <form onSubmit={handleClaimSubmit}>
              <div className="mb-4">
                <label className="block text-gray-700 font-semibold mb-2">
                  Full Name *
                </label>
                <input
                  type="text"
                  name="name"
                  value={claimData.name}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Enter your full name"
                />
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 font-semibold mb-2">
                  Email *
                </label>
                <input
                  type="email"
                  name="email"
                  value={claimData.email}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="your.email@khi.iba.edu.pk"
                />
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 font-semibold mb-2">
                  Mobile Number *
                </label>
                <input
                  type="tel"
                  name="mobile"
                  value={claimData.mobile}
                  onChange={handleInputChange}
                  required
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="03001234567"
                />
              </div>

              <div className="mb-4">
                <label className="block text-gray-700 font-semibold mb-2">
                  Additional Notes (Optional)
                </label>
                <textarea
                  name="notes"
                  value={claimData.notes}
                  onChange={handleInputChange}
                  rows="3"
                  className="w-full px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary"
                  placeholder="Provide any details that prove this is your item..."
                />
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                <p className="text-sm text-blue-800">
                  ℹ️ After submitting, please visit the Lost & Found office with your ID card for verification.
                </p>
              </div>

              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => setShowClaimModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-100"
                  disabled={loading}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="flex-1 btn-primary"
                  disabled={loading}
                >
                  {loading ? 'Submitting...' : 'Submit Claim'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
}