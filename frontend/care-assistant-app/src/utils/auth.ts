export const isAuthenticated = () => {
    return !!localStorage.getItem("token");
  };
  
  export const login = (token: string) => {
    localStorage.setItem("token", token);
  };
  
  export const logout = () => {
    localStorage.removeItem("token");
  };