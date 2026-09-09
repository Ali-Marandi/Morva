import React from "react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

export interface PayrollChartRecord {
  month: string;
  processed: number;
  pending: number;
  rejected: number;
}

interface PayrollChartProps {
  data: PayrollChartRecord[];
}

function PayrollChart({ data }: PayrollChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 20, right: 30, left: 0, bottom: 60 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e3eaf2" />
        <XAxis dataKey="month" stroke="#728197" />
        <YAxis stroke="#728197" />
        <Tooltip
          contentStyle={{
            backgroundColor: "#f4f7fb",
            border: "1px solid #dbe4ef",
            borderRadius: "8px",
          }}
          cursor={{ fill: "rgba(122, 158, 198, 0.1)" }}
        />
        <Legend wrapperStyle={{ paddingTop: "20px" }} />
        <Bar dataKey="processed" fill="#5a7fb0" name="تکمیل‌شده" radius={[8, 8, 0, 0]} />
        <Bar dataKey="pending" fill="#e67e22" name="در انتظار" radius={[8, 8, 0, 0]} />
        <Bar dataKey="rejected" fill="#27ae60" name="رد‌شده" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default PayrollChart;
