import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Containers } from './containers';

describe('Containers', () => {
  let component: Containers;
  let fixture: ComponentFixture<Containers>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Containers]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Containers);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
