import { CommonModule, NgOptimizedImage } from '@angular/common';
import { Component, OnDestroy, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth.service';
import { Router, RouterModule } from '@angular/router';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-login',
  imports: [CommonModule, FormsModule, NgOptimizedImage, RouterModule],
  templateUrl: './login.component.html',
  styleUrl: './login.component.css'
})
export class LoginComponent implements OnInit, OnDestroy {
  username: string = '';
  password: string = '';
  isLoading: boolean = false;
  currentImageIndex = 0;
  previousImageIndex = 0;
  isTransitioning = false;
  private carouselTimer: any = null;
  private transitionTimer: any = null;

  images: string[] = [
    'assets/images/fondo.png',
    'assets/images/fondo2.png',
    'assets/images/fondo3.png',
    'assets/images/fondo4.png'
  ];

  get currentBackground(): string {
    const url = this.images[this.currentImageIndex] || this.images[0];
    return `url('${url}')`;
  }

  get previousBackground(): string {
    const url = this.images[this.previousImageIndex] || this.images[0];
    return `url('${url}')`;

  }

  constructor(
    private authService: AuthService,
    private router: Router
  ) {}
  

  ngOnInit(): void {
    if (this.authService.isLoggedIn()) {
      this.router.navigateByUrl('/dashboard', { replaceUrl: true });
    }
    this.startCarousel();
  }

  ngOnDestroy(): void{
    this.stopCarousel();
  }

  private startCarousel(): void {
    if (!this.images.length) return;
    this.carouselTimer = setInterval(() => {
      this.previousImageIndex = this.currentImageIndex;
      this.currentImageIndex = (this.currentImageIndex + 1) % this.images.length;
      this.isTransitioning = true;
      if (this.transitionTimer) {
        clearTimeout(this.transitionTimer);
      }
      this.transitionTimer = setTimeout(() => {
        this.isTransitioning = false;
      }, 1200);
    }, 5000);
  }

  private stopCarousel(): void {
    if (this.carouselTimer){
      clearInterval(this.carouselTimer);
      this.carouselTimer = null;
    }
    if (this.transitionTimer) {
      clearTimeout(this.transitionTimer);
      this.transitionTimer = null;
    }
  }

  onSubmit(): void {
    if (!this.username || !this.password) {
      Swal.fire({
        icon: 'warning',
        title: 'Datos incompletos',
        text: 'Por favor, ingresa usuario y contraseña'
      });
      return;
    }

    this.isLoading = true;

    this.authService.login(this.username, this.password).subscribe({
      next: (response) =>  {
        console.log(`Acceso Exitoso`, response);
        const displayName = (response?.user?.full_name ||
          `${response?.user?.first_name ?? ''} ${response?.user?.last_name ?? ''}`
        ).trim() || this.username;
        Swal.fire({
          icon: 'success',
          title: 'Acceso exitoso',
          text: `Bienvenido ${displayName}`,
          timer: 1200,
          showConfirmButton: false
        }).then(() => {
          this.router.navigateByUrl('/dashboard', { replaceUrl: true });
        });
      },
      error: (error) => {
        console.log('Error de login', error);
        Swal.fire({
          icon: 'error',
          title: 'Error de login',
          text: 'Usuario o contraseña incorrectos'
        });
        this.isLoading = false;
      },
      complete: () => {
        this.isLoading = false;
      }
    });
  }
}
