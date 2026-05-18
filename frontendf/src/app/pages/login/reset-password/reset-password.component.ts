import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { AuthService } from '../../../services/auth.service';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-reset-password',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './reset-password.component.html',
  styleUrls: ['./reset-password.component.css']
})
export class ResetPasswordComponent implements OnInit {
  uidb64: string = '';
  token: string = '';
  password: string = '';
  passwordConfirm: string = '';
  error: string = '';
  guardando: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthService
  ) {}

  ngOnInit(): void {
    this.uidb64 = this.route.snapshot.paramMap.get('uidb64') || '';
    this.token = this.route.snapshot.paramMap.get('token') || '';
  }

  resetear(): void {
    this.error = '';

    if (!this.password || !this.passwordConfirm) {
      this.error = 'Por favor completa todos los campos';
      return;
    }

    if (this.password !== this.passwordConfirm) {
      this.error = 'Las contraseñas no coinciden';
      return;
    }

    if (this.password.length < 6) {
      this.error = 'La contraseña debe tener al menos 6 caracteres';
      return;
    }

    this.guardando = true;
    this.authService.resetPassword(this.uidb64, this.token, this.password).subscribe({
      next: () => {
        Swal.fire({
          icon: 'success',
          title: 'Contraseña actualizada',
          text: 'Ya puedes iniciar sesion con tu nueva clave.',
          confirmButtonText: 'Ir al login'
        }).then(() => {
          this.router.navigate(['/login']);
        });
      },
      error: (err) => {
        this.error = 'Token inválido o expirado. Solicita un nuevo enlace.';
        Swal.fire({
          icon: 'error',
          title: 'No se pudo restablecer',
          text: this.error
        });
        this.guardando = false;
      }
    });
  }
}
