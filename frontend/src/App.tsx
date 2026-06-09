import { Routes, Route, Navigate } from 'react-router-dom';
import { ProtectedRoute } from '@/components/layout/ProtectedRoute';
import { AdminRoute } from '@/components/layout/AdminRoute';
import { Login } from '@/pages/Login';
import { Register } from '@/pages/Register';
import { Dashboard } from '@/pages/Dashboard';
import { Upload } from '@/pages/Upload';
import { TaskStatus } from '@/pages/TaskStatus';
import { Descriptions } from '@/pages/Descriptions';
import { AdminTasks } from '@/pages/AdminTasks';

function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/upload" element={<Upload />} />
        <Route path="/task/:taskId" element={<TaskStatus />} />
        <Route path="/task/:taskId/descriptions" element={<Descriptions />} />
        <Route element={<AdminRoute />}>
          <Route path="/admin/tasks" element={<AdminTasks />} />
        </Route>
      </Route>
    </Routes>
  );
}

export default App;
