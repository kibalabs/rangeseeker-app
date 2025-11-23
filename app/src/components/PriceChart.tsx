import React, { useEffect, useRef } from 'react';

import { Box } from '@kibalabs/ui-react';
import { AreaSeries, ColorType, createChart, IChartApi, IPriceLine, LineSeries, Time } from 'lightweight-charts';

import { StrategyDefinition, UniswapPosition } from '../client/resources';

export interface PriceDataPoint {
  timestamp: number;
  price: number;
}

interface PriceChartProps {
  priceData?: PriceDataPoint[];
  strategyDefinition?: StrategyDefinition | null;
  currentPrice?: number;
  uniswapPositions?: UniswapPosition[];
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

    const priceLines: IPriceLine[] = [];

    // Sort by timestamp and remove duplicates
    const sortedData = [...props.priceData].sort((a, b) => a.timestamp - b.timestamp);
    const uniqueData: { time: Time; value: number }[] = [];
    let lastTimestamp: number | null = null;

    sortedData.forEach((point) => {
      if (lastTimestamp === null || point.timestamp > lastTimestamp) {
        uniqueData.push({
          time: point.timestamp as Time,
          value: point.price,
        });
        lastTimestamp = point.timestamp;
      }
    });

    lineSeries.setData(uniqueData);

    const areaSeries = chart.addSeries(AreaSeries, {
      topColor: 'rgba(46, 228, 227, 0.2)',
      bottomColor: 'rgba(46, 228, 227, 0.0)',
      lineColor: 'transparent',
      lineWidth: 1,
    });
    areaSeries.setData(uniqueData);

    // Set visible range to show last 24 hours by default and prevent scrolling beyond data range
    if (uniqueData.length > 0) {
      const firstTimestamp = uniqueData[0].time as number;
      const lastDataTimestamp = uniqueData[uniqueData.length - 1].time as number;
      const oneDayAgo = lastDataTimestamp - (24 * 60 * 60);

      chart.timeScale().setVisibleRange({
        from: oneDayAgo as Time,
        to: lastDataTimestamp as Time,
      });

      // Prevent scrolling beyond data bounds
      chart.timeScale().subscribeVisibleTimeRangeChange((timeRange) => {
        if (timeRange !== null) {
          const fromTime = timeRange.from as number;
          const toTime = timeRange.to as number;
          const rangeWidth = toTime - fromTime;

          // If user scrolled too far left (before first data point)
          if (fromTime < firstTimestamp) {
            chart.timeScale().setVisibleRange({
              from: firstTimestamp as Time,
              to: (firstTimestamp + rangeWidth) as Time,
            });
          } else if (toTime > lastDataTimestamp) {
            // If user scrolled too far right (beyond last data point)
            chart.timeScale().setVisibleRange({
              from: (lastDataTimestamp - rangeWidth) as Time,
              to: lastDataTimestamp as Time,
            });
          }
        }
      });
    }

    // Helper function to convert tick to price
    const tickToPrice = (tick: number): number => {
      return 1.0001 ** tick;
    };

    // Add current position bands
    if (props.uniswapPositions && props.uniswapPositions.length > 0) {
      props.uniswapPositions.forEach((position, index) => {
        if (position.tickLower !== null && position.tickUpper !== null) {
          const priceLower = tickToPrice(position.tickLower);
          const priceUpper = tickToPrice(position.tickUpper);

          priceLines.push(
            lineSeries.createPriceLine({
              price: priceLower,
              color: '#00FF00',
              lineWidth: 2,
              lineStyle: 0,
              axisLabelVisible: true,
              title: `Position ${index + 1} Lower`,
            }),
            lineSeries.createPriceLine({
              price: priceUpper,
              color: '#00FF00',
              lineWidth: 2,
              lineStyle: 0,
              axisLabelVisible: true,
              title: `Position ${index + 1} Upper`,
            }),
          );
        }
      });
    }

    // Add strategy overlays
    if (props.strategyDefinition && props.strategyDefinition.rules && props.currentPrice) {
      console.log('Drawing strategy overlays:', {
        rulesCount: props.strategyDefinition.rules.length,
        currentPrice: props.currentPrice,
        rules: props.strategyDefinition.rules,
      });
      const rangeRule = props.strategyDefinition.rules.find((rule) => rule.type === 'RANGE_WIDTH');
      const priceThresholdRules = props.strategyDefinition.rules.filter((rule) => rule.type === 'PRICE_THRESHOLD');

      // Draw range bands
      if (rangeRule && 'baseRangePercent' in rangeRule.parameters) {
        const rangePercent = rangeRule.parameters.baseRangePercent / 100;
        const upperBound = props.currentPrice * (1 + rangePercent);
        const lowerBound = props.currentPrice * (1 - rangePercent);

        priceLines.push(
          lineSeries.createPriceLine({
            price: upperBound,
            color: '#FFA500',
            lineWidth: 2,
            lineStyle: 2,
            axisLabelVisible: true,
            title: `+${rangeRule.parameters.baseRangePercent}%`,
          }),
          lineSeries.createPriceLine({
            price: lowerBound,
            color: '#FFA500',
            lineWidth: 2,
            lineStyle: 2,
            axisLabelVisible: true,
            title: `-${rangeRule.parameters.baseRangePercent}%`,
          }),
        );

        // Draw widened range if dynamic widening exists
        if (rangeRule.parameters.dynamicWidening) {
          const widenedPercent = rangeRule.parameters.dynamicWidening.widenToPercent / 100;
          const widenedUpper = props.currentPrice * (1 + widenedPercent);
          const widenedLower = props.currentPrice * (1 - widenedPercent);

          priceLines.push(
            lineSeries.createPriceLine({
              price: widenedUpper,
              color: '#FF6B00',
              lineWidth: 1,
              lineStyle: 3,
              axisLabelVisible: true,
              title: `+${rangeRule.parameters.dynamicWidening.widenToPercent}%`,
            }),
            lineSeries.createPriceLine({
              price: widenedLower,
              color: '#FF6B00',
              lineWidth: 1,
              lineStyle: 3,
              axisLabelVisible: true,
              title: `-${rangeRule.parameters.dynamicWidening.widenToPercent}%`,
            }),
          );
        }
      }

      // Draw price thresholds
      priceThresholdRules.forEach((rule) => {
        if ('priceUsd' in rule.parameters) {
          priceLines.push(
            lineSeries.createPriceLine({
              price: rule.parameters.priceUsd,
              color: '#FF4444',
              lineWidth: 2,
              lineStyle: 0,
              axisLabelVisible: true,
              title: `$${rule.parameters.priceUsd.toLocaleString()}`,
            }),
          );
        }
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
  }, [props.priceData, props.strategyDefinition, props.currentPrice, props.uniswapPositions]);

  return (
    <Box ref={chartContainerRef} width='100%' height='100%' />
  );
}
