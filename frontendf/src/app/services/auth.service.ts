import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, BehaviorSubject, tap } from 'rxjs';


@Injectable({
  providedIn: 'root'
})
export class AuthService {
  private apiUrl = 'http://localhost:8000/api';
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(this.hasSession());
  public isAuthenticated$ = this.isAuthenticatedSubject.asObservable();

  constructor(private http: HttpClient) {}

  login(username: string, password: string): Observable<any> {
    return this.http.post(`${this.apiUrl}/login/`, 
      { username, password },
      { withCredentials: true }
    ).pipe(
      tap(() => {
        this.isAuthenticatedSubject.next(true);
        localStorage.setItem('isLoggedIn', 'true');
      })
    );
  }

  logout(): Observable<any> {
    return this.http.post(`${this.apiUrl}/logout/`, {}, 
      { withCredentials: true }
    ).pipe(
      tap(() => {
        this.isAuthenticatedSubject.next(false);
        localStorage.removeItem('isLoggedIn');
      })
    );
  }

  isLoggedIn(): boolean {
    return this.hasSession();
  }

  private hasSession(): boolean {
    return localStorage.getItem('isLoggedIn') === 'true';
  }

  getCurrentUser(): Observable<any> {
    return this.http.get(`${this.apiUrl}/user/`, { withCredentials: true });
  }
}
