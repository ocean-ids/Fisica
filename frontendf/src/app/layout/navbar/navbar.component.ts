import { Component, Input, OnInit } from '@angular/core';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';
import { Router } from '@angular/router';
import { MatMenuModule } from '@angular/material/menu';

@Component({
  selector: 'app-navbar',
  imports: [MatToolbarModule, MatIconModule, MatButtonModule, CommonModule, MatMenuModule],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css'
})
export class NavbarComponent implements OnInit {
  @Input() username?: string;
  themeMode: 'light' | 'dark' = 'light';

  constructor(
    private authService: AuthService,
    private router: Router
  ){}

  ngOnInit(): void {
    // Obtener usuario desde localStorage en lugar de hacer petición al backend
    const user = this.authService.getUserFromStorage();
    if (user) {
      this.username = user.username;
    }

    const storedTheme = localStorage.getItem('themeMode');
    this.themeMode = storedTheme === 'dark' ? 'dark' : 'light';
    this.applyThemeClass();
  }

  toggleTheme(): void {
    this.themeMode = this.themeMode === 'light' ? 'dark' : 'light';
    localStorage.setItem('themeMode', this.themeMode);
    this.applyThemeClass();
  }

  get isLightMode(): boolean {
    return this.themeMode === 'light';
  }

  private applyThemeClass(): void {
    document.body.classList.remove('theme-light', 'theme-dark');
    document.body.classList.add(`theme-${this.themeMode}`);
  }

  logout(): void{
    this.authService.logout().subscribe({
      next: () =>{
        this.router.navigate(['/login']);
      },
      error: (error)=>{
        console.log('Error al cerrar sesión');
        this.router.navigate(['/login']);
      }
    });
  }

}
