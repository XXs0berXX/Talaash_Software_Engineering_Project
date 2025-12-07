/**
 * Dashboard Page - For Authenticated Users
 * Separate sections for user's reports and browsable items
 */

import React, { useState, useEffect } from "react";
import ItemCard from "../components/ItemCard";
import axios from "axios";
import Link from "next/link";
import { useRouter } from "next/router";
import AuthGuard from "../components/AuthGuard";
import { auth } from "../lib/firebase";

function DashboardContent() {
  const [browseItems, setBrowseItems] = useState([]);
  const [myFoundItems, setMyFoundItems] = useState([]);
  const [myLostItems, setMyLostItems] = useState([]);
  const [myClaims, setMyClaims] = useState([]);
  const [loadingBrowse, setLoadingBrowse] = useState(true);
  const [loadingMyItems, setLoadingMyItems] = useState(true);
  const [loadingClaims, setLoadingClaims] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState("browse");
  const router = useRouter();

  useEffect(() => {
    fetchBrowseItems();
    fetchMyReports();
    fetchMyClaims();
  }, []);

  const fetchBrowseItems = async () => {
    try {
      setLoadingBrowse(true);
      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/found`,
        {
          params: {
            status_filter: "approved",
            limit: 12,
          },
        }
      );

      const itemsData = response.data.items || response.data || [];

      // Filter out items reported by current user
      const user = auth.currentUser;
      if (user) {
        const filteredItems = itemsData.filter(
          (item) => item.reporter_id !== user.uid
        );
        setBrowseItems(filteredItems);
      } else {
        setBrowseItems(itemsData);
      }

      setError(null);
    } catch (err) {
      console.error("Failed to fetch browse items:", err);
      setError("Failed to load items");
    } finally {
      setLoadingBrowse(false);
    }
  };

  const fetchMyReports = async () => {
    try {
      setLoadingMyItems(true);
      const user = auth.currentUser;
      if (!user) return;

      const token = await user.getIdToken();

      // Fetch found items
      const foundResponse = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/found/my-items`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      // Fetch lost items
      const lostResponse = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/lost/my-items`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setMyFoundItems(foundResponse.data.items || []);
      setMyLostItems(lostResponse.data.items || []);
    } catch (err) {
      console.error("Failed to fetch my reports:", err);
    } finally {
      setLoadingMyItems(false);
    }
  };

  const fetchMyClaims = async () => {
    try {
      setLoadingClaims(true);
      const user = auth.currentUser;
      if (!user) return;

      const token = await user.getIdToken();

      const response = await axios.get(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/claims/my-claims`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      setMyClaims(response.data.claims || []);
    } catch (err) {
      console.error("Failed to fetch my claims:", err);
    } finally {
      setLoadingClaims(false);
    }
  };

  const getStatusBadge = (status) => {
    if (status === "pending") {
      return (
        <span className="bg-yellow-100 text-yellow-800 px-3 py-1 rounded-full text-sm font-semibold">
          ⏳ Pending
        </span>
      );
    } else if (status === "approved" || status === "active") {
      return (
        <span className="bg-green-100 text-green-800 px-3 py-1 rounded-full text-sm font-semibold">
          ✅ Active
        </span>
      );
    } else if (status === "rejected") {
      return (
        <span className="bg-red-100 text-red-800 px-3 py-1 rounded-full text-sm font-semibold">
          ❌ Rejected
        </span>
      );
    } else if (status === "found") {
      return (
        <span className="bg-blue-100 text-blue-800 px-3 py-1 rounded-full text-sm font-semibold">
          🎉 Found
        </span>
      );
    }
    return null;
  };

  const handleMarkAsFound = async (itemId) => {
    if (!confirm('Mark this item as found? This will remove it from the active lost items list.')) {
      return;
    }

    try {
      const user = auth.currentUser;
      if (!user) return;

      const token = await user.getIdToken();

      const response = await axios.post(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/api/items/lost/${itemId}/mark-found`,
        {},
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );

      if (response.data.status === 'success') {
        alert('Item marked as found!');
        await fetchMyReports();
      }
    } catch (err) {
      console.error('Failed to mark item as found:', err);
      alert('Failed to mark item as found');
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Hero Section */}
      <div className="bg-gradient-to-r from-primary to-secondary text-white py-12">
        <div className="container-custom">
          <h1 className="text-4xl font-bold mb-4">Dashboard</h1>
          <p className="text-lg mb-8">
            Welcome back! What would you like to do today?
          </p>

          {/* Quick Action Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-2xl">
            <Link href="/search">
              <div className="bg-white bg-opacity-10 backdrop-blur-sm p-6 rounded-lg hover:bg-opacity-20 transition-all cursor-pointer border border-white border-opacity-20">
                <div className="text-3xl mb-2">🔍</div>
                <h3 className="text-xl font-bold mb-1">Search Items</h3>
                <p className="text-sm opacity-90">Find your lost belongings</p>
              </div>
            </Link>

            <Link href="/report-lost">
              <div className="bg-white bg-opacity-10 backdrop-blur-sm p-6 rounded-lg hover:bg-opacity-20 transition-all cursor-pointer border border-white border-opacity-20">
                <div className="text-3xl mb-2">😢</div>
                <h3 className="text-xl font-bold mb-1">Report Lost</h3>
                <p className="text-sm opacity-90">Report a lost item</p>
              </div>
            </Link>
          </div>

          {/* Info Box */}
          <div className="mt-6 bg-white bg-opacity-10 backdrop-blur-sm p-4 rounded-lg border border-white border-opacity-20 max-w-2xl">
            <p className="text-sm opacity-90">
              💡 <strong>Found something?</strong> Please submit it to the Lost
              & Found Office. Our admin will add it to the system.
            </p>
          </div>
        </div>
      </div>

      {/* How It Works Section */}
      <div className="bg-white py-12 border-b">
        <div className="container-custom">
          <h2 className="text-2xl font-bold text-center mb-8">How It Works</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            <div className="text-center">
              <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">1️⃣</span>
              </div>
              <h3 className="text-lg font-bold mb-2">Report or Search</h3>
              <p className="text-gray-600 text-sm">
                Lost something? Search our database.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">2️⃣</span>
              </div>
              <h3 className="text-lg font-bold mb-2">Admin Review</h3>
              <p className="text-gray-600 text-sm">
                Our team reviews submissions to ensure accuracy and prevent
                misuse.
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">3️⃣</span>
              </div>
              <h3 className="text-lg font-bold mb-2">Get Reunited</h3>
              <p className="text-gray-600 text-sm">
                Once approved, items are visible to help reunite them with their
                owners.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Section */}
      <div className="container-custom py-8">
        <div className="flex gap-4 mb-6">
          <button
            onClick={() => setActiveTab("browse")}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              activeTab === "browse"
                ? "bg-primary text-white shadow-lg"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            Browse Items
          </button>
          <button
            onClick={() => setActiveTab("my-reports")}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              activeTab === "my-reports"
                ? "bg-primary text-white shadow-lg"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            My Reports
          </button>
          <button
            onClick={() => setActiveTab("my-claims")}
            className={`px-6 py-3 rounded-lg font-semibold transition-all ${
              activeTab === "my-claims"
                ? "bg-primary text-white shadow-lg"
                : "bg-white text-gray-700 hover:bg-gray-100"
            }`}
          >
            My Claims ({myClaims.length})
          </button>
        </div>

        {/* Browse Items Tab */}
        {activeTab === "browse" && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">Items You Can Claim</h2>
              <Link href="/search">
                <button className="text-primary hover:underline font-semibold">
                  View All →
                </button>
              </Link>
            </div>

            {loadingBrowse ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
              </div>
            ) : error ? (
              <div className="bg-red-50 border border-red-200 text-red-700 p-4 rounded-lg text-center">
                {error}
              </div>
            ) : browseItems.length === 0 ? (
              <div className="bg-gray-100 p-8 rounded-lg text-center">
                <p className="text-gray-600 mb-4">
                  No items available to claim
                </p>
                <p className="text-sm text-gray-500">
                  Items reported by other users will appear here
                </p>
              </div>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {browseItems.map((item) => (
                  <ItemCard
                    key={item.id}
                    item={item}
                    type="found"
                    showClaimButton={true}
                  />
                ))}
              </div>
            )}
          </div>
        )}

        {/* My Reports Tab */}
        {activeTab === "my-reports" && (
          <div>
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-2xl font-bold">My Reported Items</h2>
            </div>

            {loadingMyItems ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
              </div>
            ) : (
              <>
                {/* Found Items */}
                {myFoundItems.length > 0 && (
                  <div className="mb-8">
                    <h3 className="text-xl font-semibold mb-4">
                      Found Items ({myFoundItems.length})
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {myFoundItems.map((item) => (
                        <div key={item.id} className="relative">
                          <ItemCard
                            item={item}
                            type="found"
                            showClaimButton={false}
                          />
                          <div className="absolute top-4 right-4">
                            {getStatusBadge(item.status)}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Lost Items */}
                {myLostItems.length > 0 && (
                  <div>
                    <h3 className="text-xl font-semibold mb-4">
                      Lost Items ({myLostItems.length})
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {myLostItems.map((item) => (
                        <div key={item.id} className="relative">
                          <ItemCard
                            item={item}
                            type="lost"
                            showClaimButton={false}
                          />
                          <div className="absolute top-4 right-4">
                            {getStatusBadge(item.status)}
                          </div>
                          {item.status === "active" && (
                            <div className="absolute bottom-4 left-4 right-4">
                              <button
                                onClick={() => handleMarkAsFound(item.id)}
                                className="w-full bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 font-semibold text-sm"
                              >
                                ✓ Mark as Found
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Empty State */}
                {myFoundItems.length === 0 && myLostItems.length === 0 && (
                  <div className="bg-gray-100 p-8 rounded-lg text-center">
                    <p className="text-gray-600 mb-4">
                      You haven't reported any items yet
                    </p>
                    <div className="flex justify-center">
                      <Link href="/report-lost">
                        <button className="bg-secondary text-white px-6 py-2 rounded-lg hover:bg-opacity-90">
                          Report Lost Item
                        </button>
                      </Link>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* My Claims Tab */}
        {activeTab === "my-claims" && (
          <div>
            <h2 className="text-2xl font-bold mb-6">My Claim Requests</h2>

            {loadingClaims ? (
              <div className="flex justify-center items-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-4 border-primary border-t-transparent"></div>
              </div>
            ) : myClaims.length === 0 ? (
              <div className="bg-gray-100 p-8 rounded-lg text-center">
                <p className="text-gray-600 mb-4">
                  You haven't submitted any claim requests yet
                </p>
                <p className="text-sm text-gray-500">
                  Claims you make on found items will appear here
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {myClaims.map((claim) => (
                  <div
                    key={claim.claim_id}
                    className={`border-2 rounded-lg p-6 ${
                      claim.status === 'approved' ? 'border-green-300 bg-green-50' :
                      claim.status === 'rejected' ? 'border-red-300 bg-red-50' :
                      'border-gray-200 bg-white'
                    }`}
                  >
                    <div className="flex gap-6">
                      {claim.item.image_url && (
                        <div className="flex-shrink-0">
                          <img
                            src={`${process.env.NEXT_PUBLIC_BACKEND_URL}${claim.item.image_url}`}
                            alt={claim.item.description}
                            className="w-32 h-32 object-cover rounded-lg border-2 border-gray-200"
                          />
                        </div>
                      )}

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

                        {claim.status === 'pending' && (
                          <div className="mt-3 bg-yellow-50 border border-yellow-200 rounded p-3">
                            <p className="text-sm text-yellow-800">
                              ⏳ Your claim is being reviewed by an admin.
                            </p>
                          </div>
                        )}

                        {claim.status === 'approved' && (
                          <div className="mt-3 bg-green-50 border border-green-200 rounded p-3">
                            <p className="text-sm text-green-800 font-semibold mb-1">
                              ✅ Your claim has been approved!
                            </p>
                            <p className="text-sm text-green-700">
                              Please visit the Lost & Found office to collect your item.
                            </p>
                            {claim.admin_notes && (
                              <p className="text-sm text-green-700 mt-2">
                                <strong>Admin notes:</strong> {claim.admin_notes}
                              </p>
                            )}
                          </div>
                        )}

                        {claim.status === 'rejected' && (
                          <div className="mt-3 bg-red-50 border border-red-200 rounded p-3">
                            <p className="text-sm text-red-800 font-semibold mb-1">
                              ❌ Your claim was not approved
                            </p>
                            {claim.admin_notes && (
                              <p className="text-sm text-red-700">
                                <strong>Reason:</strong> {claim.admin_notes}
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <footer className="bg-dark text-white py-8">
        <div className="container-custom text-center">
          <p className="mb-2">&copy; 2024 Talash - Campus Lost and Found</p>
          <p className="text-sm text-gray-400">IBA University</p>
        </div>
      </footer>
    </div>
  );
}

export default function Dashboard() {
  return (
    <AuthGuard>
      <DashboardContent />
    </AuthGuard>
  );
}