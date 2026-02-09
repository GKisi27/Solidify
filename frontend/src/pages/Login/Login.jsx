import React from "react";
import "./Login.scss";
import VisibilityIcon from "@mui/icons-material/Visibility";
export default function Login() {
  return (
    <div className="Login">
      <div className="container">
        <div className="header">
          <h2>Log in to Solidify</h2>
          <span>Access your 3D conversion workplace.</span>
        </div>

        <form>
          <div className="fields">
            <div className="username-field">
              <label>Username</label>
              <input type="text" placeholder="Username" name="username"></input>
            </div>

            <div className="password">
              <label>Password</label>
              <div className="password-input">
                <input
                  type="password"
                  placeholder="Password"
                  name="password"
                ></input>
                <VisibilityIcon className="eye"></VisibilityIcon>
              </div>
              <span>Forgot Password?</span>
            </div>
          </div>
          <button>Login</button>
        </form>
      </div>
    </div>
  );
}
