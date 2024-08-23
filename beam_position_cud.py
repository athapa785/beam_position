# Author: Adi Thapa

import sys
import time
import numpy as np
import matplotlib.pyplot as plt
from PyQt5.QtWidgets import QApplication, QMainWindow, QGridLayout, QWidget, QSlider, QLabel, QSizePolicy, QSpinBox, QPushButton, QFrame, QCheckBox
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QTimer
import epics
from datetime import datetime, timedelta
import matplotlib.dates as mdates
from matplotlib.font_manager import FontProperties
import pandas as pd
from scipy import stats
from PyQt5 import QtTest
import seaborn as sns
import qdarkstyle

class RealTimePlot(QWidget):
    def __init__(self, parent=None):
        super(RealTimePlot, self).__init__(parent)
        
        # Create the layout
        self.layout = QGridLayout()
        self.setLayout(self.layout)
        
        # Max number of data points to save
        self.num_points = 50000

        # Centroid sample size
        self.centroid_sample_size = 240
        
       
        # Add inputs
        self.plot_window_label = QLabel("Plot Window (No. of Points):")
        self.layout.addWidget(self.plot_window_label, 5, 6)
        self.plot_window_input = QSpinBox()
        self.plot_window_input.setMaximum(self.num_points )
        self.plot_window_input.setMinimum(250)
        self.plot_window_input.setSingleStep(50)
        self.plot_window_input.editingFinished.connect(self.check_minimum_value)
        self.plot_window_input.setValue(1200)
        self.layout.addWidget(self.plot_window_input, 5, 7)
        
        self.points_to_plot_label = QLabel("Points in 'Beam Position' Cloud:")
        self.layout.addWidget(self.points_to_plot_label, 6, 6)
        self.points_to_plot_input = QSpinBox()
        self.points_to_plot_input.setMaximum(self.num_points)
        self.points_to_plot_input.setMinimum(0)
        self.points_to_plot_input.setValue(800)
        self.points_to_plot_input.setSingleStep(100)
        self.layout.addWidget(self.points_to_plot_input, 6, 7)
        
        self.number_centroids_label = QLabel("No. of Centroid Markers:")
        self.layout.addWidget(self.number_centroids_label, 7, 6)
        self.number_centroids_input = QSpinBox()
        self.number_centroids_input.setMaximum(self.num_points )
        self.number_centroids_input.setMinimum(0)
        self.number_centroids_input.setValue(800)
        self.number_centroids_input.setMinimum(0)
        self.number_centroids_input.setSingleStep(100)
        self.layout.addWidget(self.number_centroids_input, 7, 7)
        
        
        
        # Theme toggler
        
        self.toggle_theme = QCheckBox("Dark Mode")
        self.toggle_theme.stateChanged.connect(self.on_toggle)
        self.layout.addWidget(self.toggle_theme, 0, 7)
         
        # Create the figure and subplots using plt.subplot_mosaic
        self.figure, axd = plt.subplot_mosaic([['ax', 'ax1'],
                                                ['ax2', 'ax1']],
                                               figsize=(15, 6), linewidth=2)
        
        self.ax = axd['ax']
        self.ax1 = axd['ax1']
        self.ax2 = axd['ax2']
        
        self.figure.subplots_adjust(left=0.05, right=1, top=0.95, bottom=0.05)
        self.figure.subplots_adjust(wspace=0)
        
        self.alphas = np.linspace(0.05, 1, self.points_to_plot_input.value())
        
        # Plot initialization
        self.line, = self.ax.plot([], [], 'ro-', label="HX2:SB1:BMMON:XPOS", alpha =0.1, linewidth=0.8)
        self.centroid_plot_x, = self.ax.plot([], [], 'b-', label=r"Centroid$_{X}$", linewidth=2.5)
        
        self.line2, = self.ax2.plot([], [], 'o-', label="HX2:SB1:BMMON:YPOS", alpha=0.15, linewidth=0.8)
        self.centroid_plot_y, = self.ax2.plot([], [], 'r-', label=r"Centroid$_{Y}$", linewidth=2.5)
        
        self.beam, = self.ax1.plot([], [], 'co', alpha=0.05, markersize=10)
        self.centroid, = self.ax1.plot([], [], color='black', marker='+', markersize=50, markeredgewidth=0.2, linestyle='None', alpha=0.05)
        self.current_marker, = self.ax1.plot([], [], color = 'red', marker = '+', markersize = 100, markeredgewidth = 2, alpha=1)
        
        
        # Axes settings
        self.ax.set_ylabel('X position (mm)')
        self.ax2.set_ylabel('Y position (mm)')
        #self.ax.grid('off')
        self.ax1.grid('on')
        #self.ax2.grid('off')
        self.ax1.set_aspect('equal')
        
        
        

        
        
        
        #Add some horizontal line
        self.hline0 = QFrame()
        self.hline0.setFrameShape(QFrame.HLine)
        self.hline0.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(self.hline0, 4, 0, 1, 8)
        
        self.hline1 = QFrame()
        self.hline1.setFrameShape(QFrame.HLine)
        self.hline1.setFrameShadow(QFrame.Sunken)
        self.layout.addWidget(self.hline1, 10, 0, 1, 8)
        
        
        
        
        
        # Add the figure canvas to the layout:
        self.layout.addWidget(self.figure.canvas, 2, 0, 1, 8)
        self.figure.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        

        # Add a slider to control the size of Plot 2
        self.slider_label = QLabel("Beam Tracker Zoom: Level 1")
        self.slider_label.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Preferred)
        self.layout.addWidget(self.slider_label, 3, 4)
    
        self.slider = QSlider()
        self.slider.setOrientation(1)  # Set orientation to horizontal
        self.slider.setMinimum(1)  # Minimum value
        self.slider.setMaximum(11)  # Maximum value
        self.slider.setValue(1)  # Initial value
        self.slider.setTickInterval(1)  # Tick interval
        self.slider.setTickPosition(QSlider.TicksBelow)  # Tick position
        self.slider.valueChanged.connect(self.update_plot_size)
        self.layout.addWidget(self.slider, 3, 5, 1, 2)
 

        #font size
        self.font = QFont()
        self.font.setPointSize(22)
        self.font.setFamily("Segoe UI")
        
        self.font2 = QFont()
        self.font2.setPointSize(40)
        self.font2.setFamily("Segoe UI")
        
 
        # Add message box
        self.msg_box = QLabel("")
        self.layout.addWidget(self.msg_box, 11, 0, 1, 3)
        self.msg_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        
        # Initialize data arrays
        self.xdata = []
        self.ydata1 = []
        self.ydata2 = []
        self.centroid_x = [] 
        self.centroid_y = []
        
        
        # GUI Title
        self.gui_title = QLabel("Photon Beam Position")
        self.gui_title.setFont(self.font2)
        self.layout.addWidget(self.gui_title, 0, 0)
        
        
        # Add stats
        self.stats_label = QLabel("Stats")
        self.stats_label.setFont(self.font)
        self.layout.addWidget(self.stats_label, 3, 0)
        
        self.drift_label = QLabel("Drift (past 1/2 hr):")
        self.layout.addWidget(self.drift_label, 5, 0) 
        self.drift_label.setFont(self.font)
        
        self.drift_from_marker = QLabel("Drift (from reference):")
        self.layout.addWidget(self.drift_from_marker, 5, 2)
        self.drift_from_marker.setFont(self.font)
        
        self.stdevx_label = QLabel("Standard Deviation in X:")
        self.layout.addWidget(self.stdevx_label, 6, 0)
        self.stdevx_label.setFont(self.font)
        
        self.stdevy_label = QLabel("Standard Deviation in Y:")
        self.layout.addWidget(self.stdevy_label, 7, 0)
        self.stdevy_label.setFont(self.font)
       
        self.spreadx_label = QLabel("Beam Spread (X):")
        self.layout.addWidget(self.spreadx_label, 6, 2) 
        self.spreadx_label.setFont(self.font)
        
        self.spready_label = QLabel("Beam Spread (Y):")
        self.layout.addWidget(self.spready_label, 7, 2)
        self.spready_label.setFont(self.font)


        # Start the timers for real-time updates
        self.timer = self.startTimer(83)
        

        # Add button to concatenate data and save as CSV
        self.save_button = QPushButton("Save Data")
        self.save_button.clicked.connect(self.save_data)
        self.layout.addWidget(self.save_button, 11, 7)
        

        
        # Reference marker
        
        self.marker = QPushButton("Reference Marker")
        self.marker.clicked.connect(self.set_marker)
        self.layout.addWidget(self.marker, 0, 5)
        
        # Remove marker
        
        self.rm_marker = QPushButton("Remove Reference Marker")
        self.rm_marker.clicked.connect(self.remove_marker)
        self.layout.addWidget(self.rm_marker, 0, 6)
        
        
        
    def timerEvent(self, event):
        
        # Get current time
        now = datetime.now()
        
        # Append new data points
        self.xdata.append(now)
        
        temp_x = epics.caget('HX2:SB1:BMMON:XPOS')
        temp_y = epics.caget('HX2:SB1:BMMON:YPOS')
        

        # filtering
        
        sd_x =  np.nanstd(self.ydata1)
        sd_y =  np.nanstd(self.ydata2)
        med_x = np.nanmedian(self.ydata1)
        med_y = np.nanmedian(self.ydata2)
        
        if len(self.xdata) < 240:
            if abs(temp_x) < 5 and abs(temp_y) < 5:
                self.ydata1.append(temp_x)
                self.ydata2.append(temp_y)
            else:
                self.ydata1.append(float('nan'))
                self.ydata2.append(float('nan'))
        else:
            if ((temp_x < med_x + 10*sd_x) and (temp_x > med_x - 10*sd_x)) and ((temp_y < med_y + 10*sd_y) and (temp_y > med_y - 10*sd_y)):
                self.ydata1.append(temp_x)
                self.ydata2.append(temp_y)
            else:
                self.ydata1.append(float('nan'))
                self.ydata2.append(float('nan'))
        
        
        # Calculate centroid
        if len(self.xdata) > self.centroid_sample_size:
            self.centroid_x.append(np.nanmedian(self.ydata1[-self.centroid_sample_size:]))
            self.centroid_y.append(np.nanmedian(self.ydata2[-self.centroid_sample_size:]))
        else:
            self.centroid_x.append(float('nan'))
            self.centroid_y.append(float('nan'))
        
        # Discard points before set number of points    
        if len(self.xdata) > self.num_points:
            self.xdata.pop(0)
            self.ydata1.pop(0)
            self.ydata2.pop(0)
            self.centroid_x.pop(0)
            self.centroid_y.pop(0)    
        
        # Plot size params
        plot_window = self.plot_window_input.value()
        start_index = max(0, len(self.xdata) - plot_window)
        points_to_plot = self.points_to_plot_input.value()
        number_of_centroids = self.number_centroids_input.value()
        
        sd_now_x =  np.nanstd(self.ydata1[plot_window:])
        sd_now_y =  np.nanstd(self.ydata2[plot_window:])
        

        
        # Update Beam tracker plot
        # Beam tracker
        self.beam.set_xdata(self.ydata1[-points_to_plot:])
        self.beam.set_ydata(self.ydata2[-points_to_plot:])
        self.ax1.relim()
        self.ax1.autoscale_view()
        try:
            size_factor = self.slider.value()
            self.ax1.set_xlim(np.nanmedian(self.centroid_x[-number_of_centroids:])-size_factor/2, np.nanmedian(self.centroid_x[-plot_window:])+size_factor/2)
            self.ax1.set_ylim(np.nanmedian(self.centroid_y[-number_of_centroids:])-size_factor/2, np.nanmedian(self.centroid_y[-plot_window:])+size_factor/2)
        except Exception:
            self.ax1.set_xlim(-1, 1)
            self.ax1.set_ylim(-1, 1)
        
        #Centroid marker
        self.centroid.set_xdata(self.centroid_x[-number_of_centroids:])
        self.centroid.set_ydata(self.centroid_y[-number_of_centroids:])
         
        
        # Update time series plots
        self.centroid_plot_x.set_xdata(self.xdata[start_index:])
        self.centroid_plot_x.set_ydata(self.centroid_x[start_index:])   #Centroid_x trace
        
        self.centroid_plot_y.set_xdata(self.xdata[start_index:])
        self.centroid_plot_y.set_ydata(self.centroid_y[start_index:])    #Centroid_y trace   
        
        self.line.set_xdata(self.xdata[start_index:])
        self.line.set_ydata(self.ydata1[start_index:])     # Raw x
        
        self.line2.set_xdata(self.xdata[start_index:])
        self.line2.set_ydata(self.ydata2[start_index:])    # Raw y
        
        try:
            self.ax.set_ylim(np.nanmedian(self.centroid_x[-plot_window:])-size_factor/2, np.nanmedian(self.centroid_x[-plot_window:])+size_factor/2)
        except Exception:
            self.ax.set_ylim(-2,2)
            
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.ax.legend()
        
        try:
            self.ax2.set_ylim(np.nanmedian(self.centroid_y[-plot_window:])-size_factor/2, np.nanmedian(self.centroid_y[-plot_window:])+size_factor/2)
        except Exception:
            self.ax2.set_ylim(-2,2)
            
        self.ax2.relim()
        self.ax2.autoscale_view()
        self.ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))
        self.ax2.legend()
        
        
        try:
            cent_x_val = self.centroid_x[-1]
            cent_y_val = self.centroid_y[-1]
            print_cent_x = r"Centroid$_{\mathbf{X}}$: " + f'{cent_x_val:.{4}f}' + '          '
            print_cent_y = r"Centroid$_{\mathbf{Y}}$: " + f'{cent_y_val:.{4}f}' + '          '
            
        except Exception:
            print_cent_x = r"Centroid$_{\mathbf{X}}$:         "
            print_cent_y = r"Centroid$_{\mathbf{Y}}$:         " 
        
        centroid_info = self.ax1.legend([print_cent_x + '\n' + print_cent_y], loc='upper left', prop=FontProperties(weight='bold', size=12))
        centroid_info.legend_handles[0].set_visible(False)

        
        self.figure.canvas.draw()
        
        try:
            # drift
            x1_x2 = self.centroid_x[-12000] - self.centroid_x[-1]
            y1_y2 = self.centroid_y[-12000] - self.centroid_y[-1]

        
            drift = np.sqrt(x1_x2**2 + y1_y2**2)
        
            self.drift_label.setText(f"Drift (past 1/2 hr): {drift:.{2}f}")
            
        except Exception:
            pass    
            
        try:
            # drift from marker
            if self.current_marker_x != float('nan'):
                x1_x2_m = self.current_marker_x - self.centroid_x[-1]
                y1_y2_m = self.current_marker_y - self.centroid_y[-1]
                
                drift_m = np.sqrt(x1_x2_m**2 + y1_y2_m**2)
        
                self.drift_from_marker.setText(f"Drift (from reference): {drift_m:.{2}f}")  
            else:
                self.drift_from_marker.setText(f"Drift (from reference):")       
        except Exception:
            pass 

         
            
        try:
            # standard deviation
            stdevx = np.nanstd(self.ydata1[-points_to_plot:])
            stdevy = np.nanstd(self.ydata2[-points_to_plot:])
        
            self.stdevx_label.setText(f"Standard Deviation in X: {stdevx:.{2}f}")
            self.stdevy_label.setText(f"Standard Deviation in Y: {stdevy:.{2}f}")
            
        except Exception:
            pass    
                
        
        try:
            # beam spread
            
            spreadx = stdevx * 2
            x_spread_upper = self.centroid_x[-1] + spreadx
            x_spread_lower = self.centroid_x[-1] - spreadx
            sizex = spreadx * 2
            
            spready = stdevy * 2
            y_spread_upper = self.centroid_y[-1] + spreadx
            y_spread_lower = self.centroid_y[-1] - spreadx
            sizey = spready * 2
            
        
            self.spreadx_label.setText(f"Beam Spread (X): ({x_spread_lower:.{2}f}, {x_spread_upper:.{2}f}) | {sizex:.{2}f}")
            self.spready_label.setText(f"Bream Spread (Y): ({y_spread_lower:.{2}f}, {y_spread_upper:.{2}f}) | {sizey:.{2}f}")
            
        except Exception:
            pass 
        
    

    def closeEvent(self, event):
        self.killTimer(self.timer)
    
  
    def update_plot_size(self):
        size_factor = self.slider.value()
        self.slider_label.setText(f"Beam Tracker Zoom: Level {size_factor}")
        
    def check_minimum_value(self):
        sender = self.sender()
        if isinstance(sender, QSpinBox):
            if sender.value() < sender.minimum():
                sender.setValue(sender.minimum())
                
    def save_data(self):
        df = pd.DataFrame({'Time':self.xdata, 'X_position':self.ydata1, 'Y_position':self.ydata2, 'Centroid_X':self.centroid_x, 'Centroid_Y':self.centroid_y})
        
        now_ = datetime.now()
        now_string = now_.strftime("%Y_%m_%d__%H_%M_%S")
        filename = 'beam_position_'+ str(now_string) + '.csv'
        #save DataFrame as CSV file
        df.to_csv(filename, index=False)
        
        self.msg_box.setText("Data saved successfully.")
        QtTest.QTest.qWait(5000)
        self.reset_msg_text()
        
    
    def on_toggle(self, state):
        if state ==2:
            self.figure.patch.set_color('gray')
            self.ax.patch.set_color('#323332')
            self.ax1.patch.set_color('#323332')
            self.ax2.patch.set_color('#323332')
            self.line.set_color('lime')
            self.centroid_plot_x.set_color('yellow')
            self.line2.set_color('orange')
            self.centroid_plot_y.set_color('lime')
            self.beam.set_color('#FF00FF')
            self.centroid.set_color('white')
            self.centroid.set_alpha(0.1)
            self.current_marker.set_color('lime')
            
        else:
            self.figure.patch.set_color('white')   
            self.ax.patch.set_color('white')
            self.ax1.patch.set_color('white')
            self.ax2.patch.set_color('white')
            self.line.set_color('red')
            self.centroid_plot_x.set_color('blue')
            self.line2.set_color('#1f77b4')
            self.centroid_plot_y.set_color('red')
            self.beam.set_color('cyan')
            self.centroid.set_color('black')
            self.centroid.set_alpha(0.05)  
            self.current_marker.set_color('red')      
            
        self.figure.canvas.draw()


    def set_marker(self):
        if len(self.xdata) > self.centroid_sample_size:
            self.current_marker_x = self.centroid_x[-1]
            self.current_marker_y = self.centroid_y[-1]
            self.current_marker.set_xdata(self.current_marker_x)
            self.current_marker.set_ydata(self.current_marker_y)
            self.current_time = datetime.now().strftime("%m/%d/%y  %H:%M:%S")
            self.msg_box.setText(f"Reference Marker Position: ({self.current_marker_x:.{4}f}, {self.current_marker_y:.{4}f}); ({self.current_time})")
        else:
            self.msg_box.setText("Not enough points to calculate the beam marker. Please wait for the centroid trace/marker to appear.")
            QtTest.QTest.qWait(5000)
            self.reset_msg_text()
            
    def remove_marker(self):
        self.current_marker_x = float('nan')
        self.current_marker_y = float('nan')
        self.current_marker.set_xdata(self.current_marker_x)
        self.current_marker.set_ydata(self.current_marker_y)
        self.reset_msg_text()
    
        
    def reset_msg_text(self):
        self.msg_box.setText("")
        
         
            

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = QMainWindow()
    plot = RealTimePlot()
    window.setCentralWidget(plot)
    window.show()
    sys.exit(app.exec_())

        
        
