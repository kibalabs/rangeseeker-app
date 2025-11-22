import React, { useEffect, useRef } from 'react';

import { Box } from '@kibalabs/ui-react';
import { AreaSeries, ColorType, createChart, IChartApi, LineSeries, Time } from 'lightweight-charts';

export function MockChart() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!chartContainerRef.current) {
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

    // Generate random walk data
    const data: { time: Time; value: number }[] = [];
    let price = 3427;
    const date = new Date();
    date.setHours(date.getHours() - 24);

    for (let i = 0; i < 1000; i += 1) {
      price += (Math.random() - 0.5) * 10;
      date.setMinutes(date.getMinutes() + 1);
      data.push({ time: (date.getTime() / 1000) as Time, value: price });
    }

    lineSeries.setData(data);

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: 'rgba(46, 228, 227, 0.2)',
      bottomColor: 'rgba(46, 228, 227, 0.0)',
      lineColor: 'transparent',
      lineWidth: 1,
    });
    areaSeries.setData(data);

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
  }, []);

  return (
    <Box ref={chartContainerRef} width='100%' height='100%' />
  );
}
