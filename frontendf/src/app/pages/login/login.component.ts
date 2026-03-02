import { CommonModule, NgOptimizedImage } from '@angular/common';
import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { Router, RouterModule } from '@angular/router';

@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule, NgOptimizedImage, RouterModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent {
  username: string = '';
  password: string = '';
  errorMessage: string = '';
  isLoading: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  onSubmit(): void {
    if (!this.username || !this.password) {
      this.errorMessage = 'Por favor, ingresa usuario y contraseña';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.authService.login(this.username, this.password).subscribe({
      next: (response) =>  {
        console.log('Acceso Exitoso', response);
        this.router.navigate(['/dashboard']);
      },
      error: (error) => {
        console.log('Error de login', error);
        this.errorMessage = 'Usuario o contraseña incorrectos';
        this.isLoading = false;
      },
      complete: () => {
        this.isLoading = false;
      }
    });
  }
}
