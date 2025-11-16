// frontend/src/pages/_app.jsx

import '../styles/globals.css';
import { useRouter } from 'next/router';
import Navbar from '../components/Navbar';

function MyApp({ Component, pageProps }) {
  const router = useRouter();
  
  // Pages that should NOT show the navbar
  const noNavbarPages = [
    '/',           // Landing page (has its own design)
    '/login',      // Login page (has its own navbar)
    '/signup',     // Signup page (has its own navbar)
    '/admin/login' // Admin login page (has its own navbar)
  ];
  
  // Check if current page should show navbar
  const showNavbar = !noNavbarPages.includes(router.pathname);

  return (
    <>
      {/* Only show navbar on pages that need it */}
      {showNavbar && <Navbar />}
      
      {/* Render the active page */}
      <Component {...pageProps} />
    </>
  );
}

export default MyApp;