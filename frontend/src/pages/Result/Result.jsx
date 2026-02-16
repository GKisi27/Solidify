import React from "react";
import "./Result.scss";
import ArchitectureOutlinedIcon from "@mui/icons-material/ArchitectureOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ViewInArOutlinedIcon from "@mui/icons-material/ViewInArOutlined";
import ImageOutlinedIcon from "@mui/icons-material/ImageOutlined";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import FullscreenOutlinedIcon from "@mui/icons-material/FullscreenOutlined";
export default function Result() {
  return (
    <div className="result">
      <div className="header">
        <div className="description">
          <h2>Conversion Results</h2>
          <span>Observe and check your input image and the conversion.</span>
        </div>

        <div className="buttons">
          <button className="first-button"> Download All</button>
          <button className="second-button">Open in Onshape</button>
        </div>
      </div>
      <div className="main">
        <div className="first">
          <div className="image-first image">
            <div className="header-bar header">
              <div className="left-part">
                <ImageOutlinedIcon className="left-icon"></ImageOutlinedIcon>
                <span>Original Input Image</span>
              </div>
              <div className="right-part">
                <FileDownloadOutlinedIcon className="right-icon"></FileDownloadOutlinedIcon>
                <FullscreenOutlinedIcon className="right-icon"></FullscreenOutlinedIcon>
              </div>
            </div>
          </div>
          <div className="image-second image">
            <div className="header-bar header">
              <div className="left-part">
                <ViewInArOutlinedIcon className="left-icon"></ViewInArOutlinedIcon>
                <span>Onshape 3D</span>
              </div>
              <div className="right-part">
                <FileDownloadOutlinedIcon className="right-icon"></FileDownloadOutlinedIcon>
                <FullscreenOutlinedIcon className="right-icon"></FullscreenOutlinedIcon>
              </div>
            </div>
          </div>
        </div>
        <div className="second">
          <div className="image-third image">
            <div className="header-bar header">
              <div className="left-part">
                <DescriptionOutlinedIcon className="left-icon"></DescriptionOutlinedIcon>
                <span>Base Mesh JSON</span>
              </div>
              <div className="right-part">
                <FileDownloadOutlinedIcon className="right-icon"></FileDownloadOutlinedIcon>
                <FullscreenOutlinedIcon className="right-icon"></FullscreenOutlinedIcon>
              </div>
            </div>
          </div>
          <div className="image-fourth image">
            <div className="header-bar header">
              <div className="left-part">
                <ArchitectureOutlinedIcon className="left-icon"></ArchitectureOutlinedIcon>
                <span>Onshape Compatible JSON</span>
              </div>
              <div className="right-part">
                <FileDownloadOutlinedIcon className="right-icon"></FileDownloadOutlinedIcon>
                <FullscreenOutlinedIcon className="right-icon"></FullscreenOutlinedIcon>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
