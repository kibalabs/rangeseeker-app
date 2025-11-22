import React, { useEffect, useRef } from 'react';

import { Box } from '@kibalabs/ui-react';
import { AreaSeries, ColorType, createChart, IChartApi, LineSeries, Time } from 'lightweight-charts';

export interface PriceDataPoint {
  timestamp: number;
  price: number;
}

interface PriceChartProps {
  priceData?: PriceDataPoint[];
}

export function PriceChart(props: PriceChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current || !props.priceData || props.priceData.length === 0) {
      return;
    }

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#DDD',
        attributionLogo: false,
      },
      grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.1)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.1)' },
      },
      width: chartContainerRef.current.clientWidth,
      height: chartContainerRef.current.clientHeight,
      timeScale: {
        timeVisible: true,
        secondsVisible: false,
      },
      trackingMode: {
        exitMode: 0, // TrackingModeExitMode.OnTouchEnd
      },
    });
    chartRef.current = chart;

    const lineSeries = chart.addSeries(LineSeries, {
      color: '#2EE4E3',
      lineWidth: 2,
    });

    // Sort by timestamp and remove duplicates
    const sortedData = [...props.priceData].sort((a, b) => a.timestamp - b.timestamp);
    const uniqueData: { time: Time; value: number }[] = [];
    let lastTimestamp: number | null = null;

    for (const point of sortedData) {
      if (lastTimestamp === null || point.timestamp > lastTimestamp) {
        uniqueData.push({
          time: point.timestamp as Time,
          value: point.price,
        });
        lastTimestamp = point.timestamp;
      }
    }

    lineSeries.setData(uniqueData);

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: 'rgba(46, 228, 227, 0.2)',
      bottomColor: 'rgba(46, 228, 227, 0.0)',
      lineColor: 'transparent',
      lineWidth: 1,
    });
    areaSeries.setData(uniqueData);

    // Set visible range to show last 24 hours by default
    if (uniqueData.length > 0) {
      const lastTimestamp = uniqueData[uniqueData.length - 1].time as number;
      const oneDayAgo = lastTimestamp - (24 * 60 * 60);
      chart.timeScale().setVisibleRange({
        from: oneDayAgo as Time,
        to: lastTimestamp as Time,
      });
    }

    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({
          width: chartContainerRef.current.clientWidth,
          height: chartContainerRef.current.clientHeight,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    // eslint-disable-next-line consistent-return
    return (): void => {
      window.removeEventListener('resize', handleResize);
      chart.remove();
    };
  }, [props.priceData]);

  return (
    <Box ref={chartContainerRef} width='100%' height='100%' />
  );
}
