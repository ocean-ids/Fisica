import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../services/auth.service';

@Component({
  selector: 'app-forgot-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './forgot-password.component.html',
  styleUrls: ['./forgot-password.component.css']
})
export class ForgotPasswordComponent {
  email: string = '';
  mensaje: string = '';
  enviando: boolean = false;

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}

  enviar(): void {
    if (!this.email) {
      alert('Por favor ingresa tu correo electrónico');
      return;
    }

    this.enviando = true;
    this.authService.solicitarResetPassword(this.email).subscribe({
      next: (response) => {
        this.mensaje = 'Si el correo existe, recibirás un email con instrucciones para restablecer tu contraseña.';
        this.enviando = false;
        this.email = '';
      },
      error: (err) => {
        console.error(err);
        this.mensaje = 'Ocurrió un error. Por favor intenta nuevamente.';
        this.enviando = false;
      }
    });
  }
}
