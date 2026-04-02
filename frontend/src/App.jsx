import './App.css';
import Footer from './components/Footer/Footer';
import Navbar from './components/Navbar/Navbar';
import LandingPage from './pages/LandingPage/LandingPage';
import CostEstimation from './pages/CostEstimation/CostEstimation';
import Login from './pages/Login/Login';
import Result from './pages/Result/Result';
import EstimateResults from './pages/Estimateresult/estimate_result';
import { isTokenExpired } from './auth';
import {
	BrowserRouter as Router,
	Routes,
	Route,
	Navigate,
} from 'react-router-dom';

function ProtectedRoute({ children }) {
	const token = localStorage.getItem('token');

	if (!token || isTokenExpired(token)) {
		return <Navigate to='/login' replace />;
	}

	return children;
}

function App() {
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
