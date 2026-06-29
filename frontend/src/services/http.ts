import axios from 'axios';

const http = axios.create({
  baseURL: 'http://localhost:8000', // Backend connection endpoint
  headers: {
    'Content-Type': 'application/json',
  },
});

http.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

http.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response) {
      const status = error.response.status;
      if (status === 401) {
        localStorage.removeItem('token');
        window.location.href = '/login';
      } else if (status === 403) {
        console.error('RBAC Access Denied: User lacks required permissions.');
      }
    }
    return Promise.reject(error);
  }
);

export default http;
