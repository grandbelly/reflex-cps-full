// Custom React components for Reflex
import React from 'react';
import HeatMapGrid from 'react-grid-heatmap';

export const CustomHeatmap = ({ data, xLabels, yLabels }) => {
  const cellRender = (x, y, value) => {
    const ratio = value / 100;
    let bgColor = '#ef4444'; // red
    if (ratio >= 0.95) bgColor = '#22c55e'; // green
    else if (ratio >= 0.8) bgColor = '#3b82f6'; // blue
    else if (ratio >= 0.6) bgColor = '#fbbf24'; // amber
    
    return (
      <div
        style={{
          width: '100%',
          height: '100%',
          backgroundColor: bgColor,
          opacity: Math.max(0.3, ratio),
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '10px',
          color: 'white',
          fontWeight: 'bold',
          border: '1px solid rgba(255,255,255,0.1)'
        }}
        title={`${yLabels[y]} ${xLabels[x]}:00 - ${value.toFixed(1)}%`}
      >
        {Math.round(value)}
      </div>
    );
  };

  return (
    <HeatMapGrid
      data={data}
      xLabels={xLabels}
      yLabels={yLabels}
      cellHeight="30px"
      square={false}
      xLabelsPos="bottom"
      yLabelsPos="left"
      cellRender={cellRender}
      xLabelsStyle={() => ({
        fontSize: '10px',
        color: '#666'
      })}
      yLabelsStyle={() => ({
        fontSize: '10px',
        color: '#666'
      })}
    />
  );
};