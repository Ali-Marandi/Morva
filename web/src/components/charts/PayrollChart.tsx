import React from "react";
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";

const data = [
  { month: "اردیبهشت", salary: 4500000, deductions: 800000, net: 3700000 },
  { month: "خرداد", salary: 4500000, deductions: 800000, net: 3700000 },
  { month: "تیر", salary: 4800000, deductions: 900000, net: 3900000 },
  { month: "مرداد", salary: 4800000, deductions: 900000, net: 3900000 },
  { month: "شهریور", salary: 5100000, deductions: 950000, net: 4150000 },
  { month: "مهر", salary: 5100000, deductions: 950000, net: 4150000 },
];

function PayrollChart() {
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
        <Bar dataKey="salary" fill="#5a7fb0" name="حقوق‌ها" radius={[8, 8, 0, 0]} />
        <Bar dataKey="deductions" fill="#e67e22" name="کسورات" radius={[8, 8, 0, 0]} />
        <Bar dataKey="net" fill="#27ae60" name="خالص" radius={[8, 8, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export default PayrollChart;
