import React from 'react';

interface KPICardProps {
  title: string;
  value: string | number;
  icon: React.ComponentType<any>;
  description: string;
  color?: string;
}

export default function KPICard({ title, value, icon: Icon, description, color = 'indigo' }: KPICardProps) {
  const getColorClasses = () => {
    switch (color) {
      case 'emerald':
        return {
          iconBg: 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20',
          glow: 'group-hover:shadow-emerald-500/5',
        };
      case 'sky':
        return {
          iconBg: 'bg-sky-500/10 text-sky-400 border border-sky-500/20',
          glow: 'group-hover:shadow-sky-500/5',
        };
      case 'amber':
        return {
          iconBg: 'bg-amber-500/10 text-amber-400 border border-amber-500/20',
          glow: 'group-hover:shadow-amber-500/5',
        };
      case 'rose':
        return {
          iconBg: 'bg-rose-500/10 text-rose-400 border border-rose-500/20',
          glow: 'group-hover:shadow-rose-500/5',
        };
      default:
        return {
          iconBg: 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/20',
          glow: 'group-hover:shadow-indigo-500/5',
        };
    }
  };

  const classes = getColorClasses();

  return (
    <div className={`glass-card p-6 rounded-xl flex items-center justify-between group glass-card-hover ${classes.glow}`}>
      <div className="space-y-2">
        <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">{title}</span>
        <h3 className="text-2xl font-bold text-slate-100 tracking-tight">{value}</h3>
        <p className="text-[10px] text-slate-500 font-medium">{description}</p>
      </div>

      <div className={`h-12 w-12 rounded-xl flex items-center justify-center ${classes.iconBg} transition-all duration-300 group-hover:scale-110`}>
        <Icon className="h-6 w-6" />
      </div>
    </div>
  );
}
