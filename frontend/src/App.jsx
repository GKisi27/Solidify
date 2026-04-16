import './App.css';
import Footer from './components/Footer/Footer';
import Navbar from './components/Navbar/Navbar';
import LandingPage from './pages/LandingPage/LandingPage';
import CostEstimation from './pages/CostEstimation/CostEstimation';
import Login from './pages/Login/Login';
import Result from './pages/Result/Result';
import EstimateResults from './pages/Estimateresult/estimate_result';
import { getStoredAccessToken, isTokenExpired } from './auth';
import { ensureAuth } from './auth';  // add this import
import {
	BrowserRouter as Router,
	Routes,
	Route,
	Navigate,
} from 'react-router-dom';

import { startTokenRefreshTimer } from './auth';
import { useState, useEffect } from 'react';


function ProtectedRoute({ children }) {
    const [ready, setReady] = useState(false);
    const [authed, setAuthed] = useState(false);

    useEffect(() => {
        ensureAuth().then(ok => {
            setAuthed(ok);
            setReady(true);
        });
    }, []);

    if (!ready) return null;
    if (!authed) return <Navigate to='/login' replace />;
    return children;
}

function App() {
    useEffect(() => {
        startTokenRefreshTimer();
    }, []);
	return (
		<Router>
			<Routes>
				{/* Login route */}
				<Route
					path='/login'
					element={
						<>
							<Login />
							<Footer />
						</>
					}
				/>

				{/* Protected Routes */}

				<Route
					path='/'
					element={
						<ProtectedRoute>
							<>
								<Navbar />
								<LandingPage />
								<Footer />
							</>
						</ProtectedRoute>
					}
				/>

				<Route
					path='/results'
					element={
						<ProtectedRoute>
							<>
								<Navbar />
								<Result />
								<Footer />
							</>
						</ProtectedRoute>
					}
				/>

				{/* Commented for cost estimation */}

				{/* <Route
					path='/cost-estimation'
					element={
						<ProtectedRoute>
							<>
								<Navbar />
								<CostEstimation />
								<Footer />
							</>
						</ProtectedRoute>
					}
				/>

				<Route
					path='/estimate-results'
					element={
						<ProtectedRoute>
							<>
								<Navbar />
								<EstimateResults />
								<Footer />
							</>
						</ProtectedRoute>
					}
				/> */}
			</Routes>
		</Router>
	);
}

export default App;
